"""O-C models beyond a polynomial ephemeris.

Light-travel-time effect (LTTE) of a third body (Irwin 1952, AJ 57, 211): the eclipsing pair orbits the
system's centre of mass, so the eclipses come early or late by
    tau(E) = A [ (1 - e^2) / (1 + e cos nu) sin(nu + omega) + e sin omega ],   A = a12 sin i / c,
with nu the true anomaly of the third-body orbit (period P3, periastron T3) at the time of minimum.
Mass function f(m3) = (a12 sin i)^3 / P3^2 (AU, years, solar masses).

Apsidal motion, first order in e (Gimenez & Garcia-Pelayo 1983, i ~ 90 deg): with omega = omega0 + d_omega E,
    T_I  = T0 + Ps E - (Pa / pi) e cos omega
    T_II = T0 + Ps E + Pa / 2 + (Pa / pi) e cos omega
so primary and secondary O-C swing in opposite directions over the apsidal period U = 360 / d_omega cycles.
shortcut: first order in e; for e > ~0.1 the higher-order terms (and the inclination) matter.

Both are fitted by searching the slow period on a grid (for a fixed period the model is linear in the rest,
or nearly) and refining every parameter with least squares.
"""

from dataclasses import dataclass

import numpy as np

AU_PER_LIGHT_DAY = 173.1446  # c x 1 day in AU
DAYS_PER_YEAR = 365.25


@dataclass
class LTTEFit:
    t0: float
    period: float
    amplitude: float  # A = a12 sin i / c, days
    p3: float  # days
    t3: float  # periastron time of the third-body orbit
    e: float
    omega: float  # deg
    errors: dict
    chi2r: float
    epochs: np.ndarray
    o_minus_c: np.ndarray
    residuals: np.ndarray
    ref_t0: float
    ref_period: float

    def tau(self, e_cycles):
        return _tau(
            self.ref_t0 + self.ref_period * np.asarray(e_cycles, float),
            self.amplitude,
            self.p3,
            self.t3,
            self.e,
            self.omega,
        )

    def model_o_minus_c(self, e_cycles, kind="I"):
        e_cycles = np.asarray(e_cycles, float)
        return (self.t0 - self.ref_t0) + (self.period - self.ref_period) * e_cycles + self.tau(e_cycles)

    @property
    def mass_function(self):
        """f(m3) in solar masses."""
        return (self.amplitude * AU_PER_LIGHT_DAY) ** 3 / (self.p3 / DAYS_PER_YEAR) ** 2


@dataclass
class ApsidalFit:
    t0: float
    period: float  # sidereal
    e: float
    omega0: float  # deg at E = 0
    d_omega: float  # deg per cycle
    errors: dict
    chi2r: float
    epochs: np.ndarray
    o_minus_c: np.ndarray
    residuals: np.ndarray
    ref_t0: float
    ref_period: float

    @property
    def u_years(self):
        """Apsidal period."""
        return 360.0 / self.d_omega * self.period / DAYS_PER_YEAR if self.d_omega else np.inf

    def model_o_minus_c(self, e_cycles, kind="I"):
        e_cycles = np.asarray(e_cycles, float)
        shift = 0.5 if kind == "II" else 0.0
        e_int = e_cycles - shift
        x = _apsidal(e_int, kind, self.t0, self.period, self.e, self.omega0, self.d_omega)
        return x - (self.ref_t0 + self.ref_period * e_cycles)


def _tau(t, a, p3, t3, e, omega_deg):
    from ..models.eb import true_anomaly

    nu = true_anomaly(t, p3, t3, e)
    w = np.radians(omega_deg)
    return a * ((1 - e**2) / (1 + e * np.cos(nu)) * np.sin(nu + w) + e * np.sin(w))


def _prepare(minima, t0_ref, period_ref):
    from .ephemeris import epochs

    times = np.array([m.time for m in minima], float)
    errs = np.array([m.error if m.error else np.nan for m in minima], float)
    errs = np.where(np.isfinite(errs), errs, np.nanmedian(errs) if np.isfinite(errs).any() else 1e-3)
    kinds = np.array([m.kind for m in minima])
    return times, errs, kinds, epochs(minima, t0_ref, period_ref)


def _covariance(sol, n):
    dof = max(1, n - len(sol.x))
    chi2r = float(np.sum(sol.fun**2) / dof)
    try:
        cov = np.linalg.inv(sol.jac.T @ sol.jac) * max(chi2r, 1.0)
        return np.sqrt(np.clip(np.diag(cov), 0, None)), chi2r
    except np.linalg.LinAlgError:
        return np.full(len(sol.x), np.nan), chi2r


def fit_ltte(minima, t0_ref, period_ref, p3_range=None):
    """Linear ephemeris + light-travel-time orbit of a third body."""
    from scipy.optimize import least_squares

    times, errs, _, e = _prepare(minima, t0_ref, period_ref)
    if len(times) < 8:
        raise ValueError("need at least 8 minima for a third-body orbit")
    base = t0_ref + period_ref * e
    span = times.max() - times.min()
    lo, hi = p3_range or (max(20 * period_ref, span / 20), 2 * span)
    best = None
    for p3 in np.geomspace(lo, hi, 300):  # circular orbit: linear in (T0, P, A cos, A sin)
        ph = 2 * np.pi * times / p3
        a = np.column_stack([np.ones_like(e), e, np.sin(ph), np.cos(ph)]) / errs[:, None]
        coef, *_ = np.linalg.lstsq(a, (times - base) / errs, rcond=None)
        chi2 = np.sum((a @ coef - (times - base) / errs) ** 2)
        if best is None or chi2 < best[0]:
            best = (chi2, p3, coef)
    _, p3, coef = best
    amp = float(np.hypot(coef[2], coef[3]))
    phase0 = np.arctan2(coef[3], coef[2])  # A sin(2 pi t/P3 + phase0) = A sin(nu + omega) for e = 0
    t3_start = -phase0 / (2 * np.pi) * p3

    t_mid = float(np.median(times))

    def resid(x):  # periastron as the mean anomaly m0 at t_mid: well scaled, no wrapping by whole orbits
        dt0, dp, a3, lp3, m0, sec, ses = x
        ecc = sec**2 + ses**2
        if ecc >= 0.95:
            return np.full(len(times), 1e6)
        w = np.degrees(np.arctan2(ses, sec))
        t3 = t_mid - m0 / (2 * np.pi) * np.exp(lp3)
        return (times - (base + dt0 + dp * e + _tau(times, a3, np.exp(lp3), t3, ecc, w))) / errs

    m_circ = 2 * np.pi * (t_mid - t3_start) / p3
    starts = [(coef[0], coef[1], amp, np.log(p3), m_circ, 0.0, 0.0)]
    for ecc0 in (0.15, 0.35, 0.6):  # eccentric starts at 8 orientations; nu + omega keeps the circular phase
        for w in np.radians(np.arange(0, 360, 45)):
            r = np.sqrt(ecc0)
            starts.append((coef[0], coef[1], amp, np.log(p3), m_circ - w, r * np.cos(w), r * np.sin(w)))
    sol = min((least_squares(resid, s, x_scale="jac") for s in starts), key=lambda r: np.sum(r.fun**2))
    err, chi2r = _covariance(sol, len(times))
    dt0, dp, a3, lp3, m0, sec, ses = sol.x
    t3 = t_mid - (m0 % (2 * np.pi)) / (2 * np.pi) * np.exp(lp3)
    ecc = float(sec**2 + ses**2)
    omega = float(np.degrees(np.arctan2(ses, sec)) % 360)
    if a3 < 0:  # the same orbit with the opposite sign of A is half a turn away in omega
        a3, omega = -a3, (omega + 180) % 360
    p3v = float(np.exp(lp3))
    fit = LTTEFit(
        t0=float(t0_ref + dt0),
        period=float(period_ref + dp),
        amplitude=float(a3),
        p3=p3v,
        t3=float(t3),
        e=ecc,
        omega=omega,
        errors={
            "t0": err[0],
            "period": err[1],
            "amplitude": err[2],
            "p3": p3v * err[3],
            "t3": p3v * err[4] / (2 * np.pi),
        },
        chi2r=chi2r,
        epochs=e,
        o_minus_c=times - base,
        residuals=sol.fun * errs,
        ref_t0=t0_ref,
        ref_period=period_ref,
    )
    return fit


def _apsidal(e_int, kinds, t0, ps, ecc, omega0, d_omega):
    w = np.radians(omega0 + d_omega * e_int)
    pa = ps / (1 - d_omega / 360.0)  # anomalistic period
    sign = np.where(np.asarray(kinds) == "II", 1.0, -1.0)
    return t0 + ps * e_int + np.where(sign > 0, pa / 2, 0.0) + sign * pa / np.pi * ecc * np.cos(w)


def fit_apsidal(minima, t0_ref, period_ref):
    """Apsidal motion from primary and secondary minima (first order in e, see the module text)."""
    from scipy.optimize import least_squares

    times, errs, kinds, e = _prepare(minima, t0_ref, period_ref)
    if (kinds == "I").sum() < 3 or (kinds == "II").sum() < 3:
        raise ValueError("apsidal motion needs at least 3 primary and 3 secondary minima")
    e_int = np.where(kinds == "II", e - 0.5, e)
    sign = np.where(kinds == "II", 1.0, -1.0)
    span = e_int.max() - e_int.min()
    best = None
    for dw in np.geomspace(360 / (20 * span), 360 / (span / 5), 400):  # linear in T0, Ps, e cos w0, e sin w0
        ph = np.radians(dw * e_int)
        pa_pi = period_ref / np.pi
        cols = [np.ones_like(e_int), e_int, sign * pa_pi * np.cos(ph), -sign * pa_pi * np.sin(ph)]
        a = np.column_stack(cols) / errs[:, None]
        y = (times - np.where(kinds == "II", period_ref / 2, 0.0)) / errs
        coef, *_ = np.linalg.lstsq(a, y, rcond=None)
        chi2 = np.sum((a @ coef - y) ** 2)
        if best is None or chi2 < best[0]:
            best = (chi2, dw, coef)
    _, dw, (t0, ps, ec, es) = best

    def resid(x):
        return (
            times - _apsidal(e_int, kinds, x[0], x[1], np.hypot(x[2], x[3]), np.degrees(np.arctan2(x[3], x[2])), x[4])
        ) / errs

    sol = least_squares(resid, (t0, ps, ec, es, dw), x_scale="jac")
    err, chi2r = _covariance(sol, len(times))
    t0, ps, ec, es, dw = sol.x
    return ApsidalFit(
        t0=float(t0),
        period=float(ps),
        e=float(np.hypot(ec, es)),
        omega0=float(np.degrees(np.arctan2(es, ec)) % 360),
        d_omega=float(dw),
        errors={"t0": err[0], "period": err[1], "d_omega": err[4]},
        chi2r=chi2r,
        epochs=e,
        o_minus_c=times - (t0_ref + period_ref * e),
        residuals=sol.fun * errs,
        ref_t0=t0_ref,
        ref_period=period_ref,
    )
