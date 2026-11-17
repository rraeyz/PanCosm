"""Linear polarimetry from photometry: Stokes q, u, degree P and angle theta.

Dual beam (half-wave plate at angles theta_i, Wollaston prism giving ordinary and extraordinary
beams; Patat & Romaniello 2006, PASP 118, 146):
    F_i = (f_o - f_e) / (f_o + f_e)
    q = (2/N) sum F_i cos(4 theta_i),   u = (2/N) sum F_i sin(4 theta_i)
With 4 or more angles spread over 0..90 deg, differences in the two beams' transmission cancel.
Single beam (polariser at 0, 45, 90, 135 deg): q = (I0 - I90)/(I0 + I90), u = (I45 - I135)/(I45 + I135).
P = sqrt(q^2 + u^2); bias-corrected P0 = sqrt(P^2 - sigma_P^2) when P > sigma_P, else 0 (Wardle &
Kronberg 1974, ApJ 194, 249); theta = 0.5 atan2(u, q) + zero point (deg, 0..180); sigma_theta = 28.65 deg sigma_P / P.
"""

import numpy as np

from ..core.citations import cites


def _result(q, u, sq, su, zero_point):
    p = float(np.hypot(q, u))
    sp = float(np.sqrt((q * sq) ** 2 + (u * su) ** 2) / p) if p > 0 else float(np.hypot(sq, su) / np.sqrt(2))
    p0 = float(np.sqrt(p * p - sp * sp)) if p > sp else 0.0
    theta = float((0.5 * np.degrees(np.arctan2(u, q)) + zero_point) % 180)
    return {
        "q": float(q),
        "q_err": float(sq),
        "u": float(u),
        "u_err": float(su),
        "p": p,
        "p_err": sp,
        "p_debiased": p0,
        "theta": theta,
        "theta_err": float(np.degrees(0.5 * sp / p)) if p > 0 else float("nan"),
    }


def dual_beam(angles_deg, f_o, f_e, err_o=None, err_e=None, zero_point=0.0):
    """q, u, P, theta from ordinary/extraordinary fluxes at half-wave-plate angles (one value per frame;
    repeated angles are fine)."""
    th = np.radians(np.asarray(angles_deg, float))
    fo, fe = np.asarray(f_o, float), np.asarray(f_e, float)
    if len(np.unique(np.round(np.degrees(th) % 90, 3))) < 2:
        raise ValueError("need half-wave-plate angles that differ (e.g. 0, 22.5, 45, 67.5)")
    s = fo + fe
    f = (fo - fe) / s
    if err_o is None or err_e is None:
        sf = np.full(len(f), np.nan)
    else:  # dF/dfo = 2 fe / s^2, dF/dfe = -2 fo / s^2
        sf = 2 * np.sqrt((fe * np.asarray(err_o, float)) ** 2 + (fo * np.asarray(err_e, float)) ** 2) / s**2
    n = len(f)
    c, sn = np.cos(4 * th), np.sin(4 * th)
    q, u = 2 / n * np.sum(f * c), 2 / n * np.sum(f * sn)
    if np.isnan(sf).any():  # no photometric errors: from the scatter of the residuals
        resid = f - (q * c + u * sn)
        sf = np.full(n, np.std(resid, ddof=min(2, n - 1)) if n > 2 else 0.0)
    sq = 2 / n * np.sqrt(np.sum((c * sf) ** 2))
    su = 2 / n * np.sqrt(np.sum((sn * sf) ** 2))
    return _result(q, u, sq, su, zero_point) | {"n": n}


def single_beam(i0, i45, i90, i135, e0=None, e45=None, e90=None, e135=None, zero_point=0.0):
    """q, u, P, theta from intensities through a polariser at 0, 45, 90 and 135 deg."""

    def norm_diff(a, b, sa, sb):
        d = (a - b) / (a + b)
        if sa is None or sb is None:
            return d, float("nan")
        return d, 2 * np.sqrt((b * sa) ** 2 + (a * sb) ** 2) / (a + b) ** 2

    q, sq = norm_diff(float(i0), float(i90), e0, e90)
    u, su = norm_diff(float(i45), float(i135), e45, e135)
    return _result(q, u, sq, su, zero_point)


@cites("wardle1974")
def debias_wk(p, sigma):
    """Wardle & Kronberg (1974): P0 = sqrt(P^2 - sigma^2) for P > sigma, else 0 (sigma: per-component error)."""
    p, sigma = np.asarray(p, float), _sigma(sigma)
    return np.sqrt(np.clip(p * p - sigma * sigma, 0, None))


@cites("plaszczynski2014")
def debias_mas(p, sigma):
    """Modified asymptotic estimator, Plaszczynski et al. (2014, MNRAS 439, 4048) eq. 3:
    P_MAS = P - sigma^2 (1 - exp(-P^2 / sigma^2)) / (2 P), isotropic noise sigma^2 = (sigma_q^2 + sigma_u^2) / 2;
    smooth at P -> 0 (gives 0 there) and tends to P for P >> sigma."""
    p, sigma = np.asarray(p, float), _sigma(sigma)
    safe = np.where(p > 0, p, 1.0)
    return np.where(p > 0, p - sigma**2 * (-np.expm1(-(safe**2) / sigma**2)) / (2 * safe), 0.0)


def _sigma(sigma):
    sigma = np.asarray(sigma, float)
    if np.any(sigma <= 0):
        raise ValueError("polarisation error must be above zero")
    return sigma


def fit_standards(q_meas, u_meas, p_cat, theta_cat, sigma=None):
    """Instrumental polarisation (q_inst, u_inst), zero-angle offset and efficiency from standard stars the caller
    gives: measured q, u (before any zero point) and the catalogue P (fraction) and theta (deg) of each star.
    Model per star: q_m = a q_c + b u_c + q_inst, u_m = -b q_c + a u_c + u_inst with q_c, u_c = P cos/sin(2 theta)
    (the measured angle is the catalogue angle minus the offset); a = e cos(2 phi), b = e sin(2 phi); weighted
    linear least squares. zero_point (deg) is the value to pass to dual_beam/single_beam. sigma: per-star error of
    q and u; omitted, it is taken from the residual scatter. Include at least one polarised standard."""
    qm, um, p, th = (np.asarray(x, float) for x in (q_meas, u_meas, p_cat, theta_cat))
    n = len(qm)
    if not (len(um) == len(p) == len(th) == n):
        raise ValueError("standard-star lists differ in length")
    if n < 2:
        raise ValueError("need at least 2 standard stars")
    qc, uc = p * np.cos(np.radians(2 * th)), p * np.sin(np.radians(2 * th))
    if not np.any(p > 0):
        raise ValueError("no polarised standard star: the zero angle cannot be fitted")
    w = np.ones(n) if sigma is None else 1 / np.broadcast_to(_sigma(sigma), n)
    z, o = np.zeros(n), np.ones(n)
    design = np.vstack([np.column_stack([qc, uc, o, z]), np.column_stack([uc, -qc, z, o])]) * np.tile(w, 2)[:, None]
    y = np.concatenate([qm, um]) * np.tile(w, 2)
    if np.linalg.matrix_rank(design) < 4:
        raise ValueError("standard stars do not fix the offset: add stars with different angles")
    coef = np.linalg.lstsq(design, y, rcond=None)[0]
    dof = 2 * n - 4
    scale = 1.0 if sigma is not None else (np.sqrt(np.sum((y - design @ coef) ** 2) / dof) if dof > 0 else np.nan)
    cov = np.linalg.inv(design.T @ design) * scale**2
    a, b, qi, ui = coef
    k2 = a * a + b * b
    var_phi = (np.array([-b, a]) @ cov[:2, :2] @ np.array([-b, a])) / k2**2
    return {
        "q_inst": float(qi),
        "q_inst_err": float(np.sqrt(cov[2, 2])),
        "u_inst": float(ui),
        "u_inst_err": float(np.sqrt(cov[3, 3])),
        "zero_point": float(np.degrees(0.5 * np.arctan2(b, a)) % 180),
        "zero_point_err": float(np.degrees(0.5 * np.sqrt(var_phi))),
        "efficiency": float(np.sqrt(k2)),
        "n": n,
    }


def correct(q, u, fit):
    """q, u in the catalogue frame: undo the fit_standards model (instrumental polarisation, rotation, efficiency)."""
    phi = np.radians(2 * fit["zero_point"])
    a, b = fit["efficiency"] * np.cos(phi), fit["efficiency"] * np.sin(phi)
    dq, du = np.asarray(q, float) - fit["q_inst"], np.asarray(u, float) - fit["u_inst"]
    k2 = a * a + b * b
    return (a * dq - b * du) / k2, (b * dq + a * du) / k2


def time_series(frames, zero_point=0.0):
    """q, u, P, theta (and errors, debiased P) per frame as JSON-friendly lists. frames: one dict per frame with
    dual_beam arguments (angles_deg, f_o, f_e and optionally err_o, err_e), e.g. one wave-plate cycle per frame."""
    rows = [dual_beam(zero_point=zero_point, **f) for f in frames]
    return {k: [r[k] for r in rows] for k in rows[0]} if rows else {}
