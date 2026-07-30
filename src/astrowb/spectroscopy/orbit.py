"""Keplerian radial-velocity orbits: single-lined (fit_orbit) and double-lined (fit_sb2: shared P, T, e,
omega, gamma; K1, K2; the secondary at omega + 180 deg).

v(t) = gamma + K [cos(nu + omega) + e cos(omega)]
mean anomaly M = 2 pi (t - T_peri) / P; Kepler's equation E - e sin E = M solved by Newton;
true anomaly nu = 2 atan2(sqrt(1+e) sin(E/2), sqrt(1-e) cos(E/2)).
Fitted with sqrt(e) cos(omega), sqrt(e) sin(omega) (well-behaved near circular orbits);
errors from the covariance, scaled by sqrt(chi2_r) when chi2_r > 1.
Mass function f(m) = P K^3 (1 - e^2)^(3/2) / (2 pi G)  [solar masses], a1 sin i = K P sqrt(1-e^2) / (2 pi).
"""

import numpy as np
from scipy.optimize import least_squares

from .. import sampling

G = 6.67430e-11
M_SUN = 1.98847e30
DAY = 86400.0
R_SUN = 6.957e8


def eccentric_anomaly(m, e, iterations=50):
    m = np.mod(m, 2 * np.pi)
    ecc = np.where(e < 0.8, m, np.pi)
    for _ in range(iterations):
        d = (ecc - e * np.sin(ecc) - m) / (1 - e * np.cos(ecc))
        ecc = ecc - d
        if np.all(np.abs(d) < 1e-12):
            break
    return ecc


def rv_model(t, period, t_peri, e, omega_deg, k, gamma):
    ecc = eccentric_anomaly(2 * np.pi * (np.asarray(t, float) - t_peri) / period, e)
    nu = 2 * np.arctan2(np.sqrt(1 + e) * np.sin(ecc / 2), np.sqrt(1 - e) * np.cos(ecc / 2))
    w = np.radians(omega_deg)
    return gamma + k * (np.cos(nu + w) + e * np.cos(w))


def _sinusoid(t, v, period, omega_deg):
    """Start values from the circular orbit (linear least squares): gamma, K and the periastron time
    that puts the maximum where omega_deg says. v = gamma + K cos(2 pi (t - T)/P + omega)."""
    ph = 2 * np.pi * np.asarray(t, float) / period
    a = np.column_stack([np.ones_like(ph), np.cos(ph), np.sin(ph)])
    g, c, s = np.linalg.lstsq(a, np.asarray(v, float), rcond=None)[0]
    theta = np.arctan2(s, c)  # v = g + K cos(ph - theta)
    return float(g), float(np.hypot(c, s)), float(period * (theta + np.radians(omega_deg)) / (2 * np.pi))


def sb2_dimensions(period_d, e, k1, k2):
    """(m1 sin^3 i, m2 sin^3 i in solar masses, a sin i in solar radii) of a double-lined orbit (Hilditch 2001,
    eq. 2.52-2.53): m1 sin^3 i = P (K1+K2)^2 K2 (1-e^2)^1.5 / (2 pi G), a sin i = P (K1+K2) (1-e^2)^0.5 / (2 pi)."""
    k1, k2 = np.abs(k1) * 1e3, np.abs(k2) * 1e3
    root = np.sqrt(1 - np.asarray(e, float) ** 2)
    base = np.asarray(period_d, float) * DAY * (k1 + k2) ** 2 * root**3 / (2 * np.pi * G) / M_SUN
    return base * k2, base * k1, (k1 + k2) * np.asarray(period_d, float) * DAY * root / (2 * np.pi) / R_SUN


def fit_orbit(t, v, err=None, period=None, t_peri=None, e=0.1, omega_deg=90.0, k=None, gamma=None, fix_period=False):
    """Least-squares SB1 orbit. Returns dict of parameters, errors, chi2r, mass function, a sin i."""
    t, v = np.asarray(t, float), np.asarray(v, float)
    w = np.ones_like(v) if err is None else 1 / np.asarray(err, float)
    tref = float(np.round(t.mean(), 1))  # small numbers for the numerical derivatives
    g0, k0, tp0 = _sinusoid(t - tref, v, period, omega_deg)
    k = k or k0
    gamma = g0 if gamma is None else gamma
    t_peri = tp0 if t_peri is None else t_peri - tref
    se, ce = np.sqrt(e) * np.sin(np.radians(omega_deg)), np.sqrt(e) * np.cos(np.radians(omega_deg))

    def unpack(p):
        per = period if fix_period else p[0]
        tp, sc, ss, kk, g = p[-5:]
        ee = sc * sc + ss * ss
        return per, tp, min(ee, 0.99), np.degrees(np.arctan2(ss, sc)), kk, g

    def resid(p):
        per, tp, ee, om, kk, g = unpack(p)
        return (rv_model(t - tref, per, tp, ee, om, kk, g) - v) * w

    p0 = ([] if fix_period else [period]) + [t_peri, ce, se, k, gamma]
    res = least_squares(resid, p0, x_scale="jac")
    dof = max(1, len(v) - len(p0))
    chi2r = float(np.sum(res.fun**2) / dof)
    cov = np.linalg.pinv(res.jac.T @ res.jac) * (chi2r if err is None else max(chi2r, 1.0))
    per, tp, ee, om, kk, g = unpack(res.x)
    # errors of derived e, omega by sampling the covariance (no linearisation of atan2 by hand)
    draws = sampling.draws(res.x, cov, 4000)
    derived = np.array([unpack(d)[2:4] for d in draws])
    sd = np.sqrt(np.diag(cov))
    kk_abs = abs(kk)
    fm = per * DAY * (kk_abs * 1e3) ** 3 * (1 - ee**2) ** 1.5 / (2 * np.pi * G) / M_SUN
    out = {
        "period": per,
        "period_err": 0.0 if fix_period else float(sd[0]),
        "t_peri": tp + tref,
        "t_peri_err": float(sd[-5]),
        "e": ee,
        "e_err": float(np.std(derived[:, 0])),
        "omega": om % 360,
        "omega_err": float(np.std(np.unwrap(np.radians(derived[:, 1]))) * 180 / np.pi),
        "k": kk_abs,
        "k_err": float(sd[-2]),
        "gamma": g,
        "gamma_err": float(sd[-1]),
        "chi2r": chi2r,
        "mass_function": float(fm),
        "a_sini_rsun": float(kk_abs * 1e3 * per * DAY * np.sqrt(1 - ee**2) / (2 * np.pi) / R_SUN),
        "rms": float(np.std(rv_model(t - tref, per, tp, ee, om, kk, g) - v)),
    }
    return out


def fit_sb2(t1, v1, t2, v2, err1=None, err2=None, period=None, fix_period=False, e=0.1, omega_deg=90.0):
    """Double-lined orbit: both components share P, T_peri, e, omega (secondary at omega + 180 deg)
    and gamma; K1, K2 free. Returns the SB1-style dict plus k2, q = K1/K2, m1 sin^3 i, m2 sin^3 i
    (solar masses) and a sin i (solar radii) of the system."""
    t1, v1, t2, v2 = (np.asarray(a, float) for a in (t1, v1, t2, v2))
    w1 = np.ones_like(v1) if err1 is None else 1 / np.asarray(err1, float)
    w2 = np.ones_like(v2) if err2 is None else 1 / np.asarray(err2, float)
    weighted = err1 is not None and err2 is not None
    tref = float(np.round(np.concatenate([t1, t2]).mean(), 1))
    se, ce = np.sqrt(e) * np.sin(np.radians(omega_deg)), np.sqrt(e) * np.cos(np.radians(omega_deg))
    g1, k1_0, tp0 = _sinusoid(t1 - tref, v1, period, omega_deg)
    g2, k2_0, _ = _sinusoid(t2 - tref, v2, period, omega_deg + 180.0)
    p0 = ([] if fix_period else [period]) + [tp0, ce, se, k1_0, k2_0, 0.5 * (g1 + g2)]

    def unpack(p):
        per = period if fix_period else p[0]
        tp, sc, ss, k1, k2, g = p[-6:]
        return per, tp, min(sc * sc + ss * ss, 0.99), np.degrees(np.arctan2(ss, sc)), k1, k2, g

    def resid(p):
        per, tp, ee, om, k1, k2, g = unpack(p)
        r1 = (rv_model(t1 - tref, per, tp, ee, om, k1, g) - v1) * w1
        r2 = (rv_model(t2 - tref, per, tp, ee, om + 180.0, k2, g) - v2) * w2
        return np.concatenate([r1, r2])

    res = least_squares(resid, p0, x_scale="jac")
    dof = max(1, len(v1) + len(v2) - len(p0))
    chi2r = float(np.sum(res.fun**2) / dof)
    cov = np.linalg.pinv(res.jac.T @ res.jac) * (max(chi2r, 1.0) if weighted else chi2r)
    per, tp, ee, om, k1, k2, g = unpack(res.x)
    draws = sampling.draws(res.x, cov, 4000)
    d = np.array([unpack(x) for x in draws])  # per, tp, e, omega, k1, k2, gamma

    m1, m2, asini = sb2_dimensions(d[:, 0], d[:, 2], d[:, 4], d[:, 5])
    sd = np.sqrt(np.diag(cov))
    r = resid(res.x)
    return {
        "period": per,
        "period_err": 0.0 if fix_period else float(sd[0]),
        "t_peri": tp + tref,
        "t_peri_err": float(sd[-6]),
        "e": ee,
        "e_err": float(np.std(d[:, 2])),
        "omega": om % 360,
        "omega_err": float(np.std(np.unwrap(np.radians(d[:, 3]))) * 180 / np.pi),
        "k": abs(k1),
        "k_err": float(sd[-3]),
        "k2": abs(k2),
        "k2_err": float(sd[-2]),
        "gamma": g,
        "gamma_err": float(sd[-1]),
        "q": abs(k1 / k2),
        "q_err": float(np.std(np.abs(d[:, 4] / d[:, 5]))),
        "m1_sin3i": float(sb2_dimensions(per, ee, k1, k2)[0]),
        "m1_sin3i_err": float(np.std(m1)),
        "m2_sin3i": float(sb2_dimensions(per, ee, k1, k2)[1]),
        "m2_sin3i_err": float(np.std(m2)),
        "a_sini_rsun": float(np.median(asini)),
        "a_sini_err": float(np.std(asini)),
        "chi2r": chi2r,
        "rms": float(np.std(r[: len(v1)] / w1)),
        "rms2": float(np.std(r[len(v1) :] / w2)),
    }
