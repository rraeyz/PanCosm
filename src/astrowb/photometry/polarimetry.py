"""Linear polarimetry from photometry: Stokes q, u, degree P and angle theta.

Dual beam (half-wave plate at angles theta_i, Wollaston prism giving ordinary and extraordinary
beams; Patat & Romaniello 2006, PASP 118, 146):
    F_i = (f_o - f_e) / (f_o + f_e)
    q = (2/N) sum F_i cos(4 theta_i),   u = (2/N) sum F_i sin(4 theta_i)
With 4 or more angles spread over 0..90 deg, differences in the two beams' transmission cancel.
Single beam (polariser at 0, 45, 90, 135 deg): q = (I0 - I90)/(I0 + I90), u = (I45 - I135)/(I45 + I135).
P = sqrt(q^2 + u^2); bias-corrected P0 = sqrt(P^2 - sigma_P^2) when P > sigma_P, else 0 (Wardle &
Kronberg 1974); theta = 0.5 atan2(u, q) + zero point (deg, 0..180); sigma_theta = 28.65 deg sigma_P / P.
"""

import numpy as np


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
