"""Double-lined spectroscopic binaries: TODCOR two-dimensional cross-correlation.

Zucker & Mazeh (1994, ApJ 420, 806). Observed spectrum f and two templates g1, g2 on a common
ln(lambda) grid, each mean-subtracted and normalised to unit length. For shifts s1, s2:
    C1(s1) = f . g1(s1),  C2(s2) = f . g2(s2),  C12(s1, s2) = g1(s1) . g2(s2)
    R(s1, s2) = [C1 + a C2] / sqrt(1 + 2 a C12 + a^2)              (fixed light ratio a)
    R^2       = [C1^2 - 2 C1 C2 C12 + C2^2] / (1 - C12^2),
    a         = (C2 - C1 C12) / (C1 - C2 C12)                         (a fitted at every point)
The maximum of R gives both velocities; it is refined by a quadratic surface through the 3x3
neighbourhood. a is in units of the normalised templates; the flux ratio of the secondary to
the primary is a * |g1'| / |g2'| (|g'| the norm of a template's line depths on the grid).
Velocity errors: Zucker (2003) maximum-likelihood form with the full 2-D Hessian of the peak and the number of
independent pixels (tests/test_sb2.py: the errors match the scatter of repeated simulations).
"""

import numpy as np

from .rv import C_KMS, v_from_ln


def _resample(grid, wave, flux):
    return np.interp(grid, np.log(np.asarray(wave, float)), np.asarray(flux, float)) - 1.0


def _unit(grid, dln, k, ln_t, t):
    """Template moved to velocity k*v_step on the grid, mean-subtracted and unit-normalised; and its norm."""
    row = np.interp(grid - k * dln, ln_t, t)
    row -= row.mean()
    norm = np.linalg.norm(row)
    return row / max(norm, 1e-30), norm


def _ccf(f, grid, dln, lags, t_wave, t_flux):
    ln_t, t = np.log(np.asarray(t_wave, float)), np.asarray(t_flux, float) - 1.0
    c, norms = np.empty(len(lags)), np.empty(len(lags))
    for i, k in enumerate(lags):
        g, norms[i] = _unit(grid, dln, k, ln_t, t)
        c[i] = f @ g
    return c, float(np.median(norms))


def todcor(wave, flux, t1_wave, t1_flux, t2_wave, t2_flux, v_min=-300.0, v_max=300.0, v_step=None, alpha=None):
    """Velocities of both components. Inputs continuum-normalised (lines below 1).

    alpha: fixed light ratio in normalised-template units; None fits it at every (v1, v2).
    Returns dict(rv1, rv2, rv1_err, rv2_err, peak, alpha, flux_ratio, v, R)."""
    wave, flux = np.asarray(wave, float), np.asarray(flux, float)
    if v_step is None:
        v_step = 0.5 * C_KMS * np.median(np.diff(np.log(wave)))
    dln = v_step / C_KMS
    lo = max(np.log(wave[0]), np.log(t1_wave[0]) - v_min / C_KMS, np.log(t2_wave[0]) - v_min / C_KMS)
    hi = min(np.log(wave[-1]), np.log(t1_wave[-1]) - v_max / C_KMS, np.log(t2_wave[-1]) - v_max / C_KMS)
    if hi - lo < 50 * dln:
        raise ValueError("observed and template spectra hardly overlap")
    grid = np.arange(lo, hi, dln)
    f = _resample(grid, wave, flux)
    f -= f.mean()
    f /= np.linalg.norm(f) + 1e-30
    lags = np.arange(int(np.floor(v_min / v_step)), int(np.ceil(v_max / v_step)) + 1)
    c1, n1 = _ccf(f, grid, dln, lags, t1_wave, t1_flux)
    c2, n2 = _ccf(f, grid, dln, lags, t2_wave, t2_flux)
    # C12 depends on s2 - s1 only (both templates move on the same log grid): one 1-D correlation
    g1, _ = _unit(grid, dln, 0, np.log(np.asarray(t1_wave, float)), np.asarray(t1_flux, float) - 1.0)
    ln2, t2 = np.log(np.asarray(t2_wave, float)), np.asarray(t2_flux, float) - 1.0
    diffs = np.arange(lags[0] - lags[-1], lags[-1] - lags[0] + 1)
    c12_d = np.array([g1 @ _unit(grid, dln, d, ln2, t2)[0] for d in diffs])
    c12 = c12_d[(lags[None, :] - lags[:, None]) - diffs[0]]
    # two stars closer than the templates' own width cannot be split: there C12 -> 1 and 1 - C12^2 -> 0 turns
    # rounding into a false peak beside the diagonal (AI Phe, one template for both, once HARPS's zero-filled gap was
    # read as missing: v1 = v2 in every spectrum). Leave out the band where the templates still overlap by half.
    centre = int(np.argmax(c12_d))
    wide = np.flatnonzero(c12_d < 0.5)
    half = int(np.min(np.abs(wide - centre))) if wide.size else 0
    blend = np.abs((lags[None, :] - lags[:, None]) - diffs[centre]) < half
    a1, a2 = c1[:, None], c2[None, :]
    with np.errstate(invalid="ignore", divide="ignore"):
        if alpha is None:
            r2 = (a1**2 - 2 * a1 * a2 * c12 + a2**2) / (1 - c12**2)
            r = np.sqrt(np.clip(r2, 0, None))
            alphas = (a2 - a1 * c12) / (a1 - a2 * c12)
            r = np.where((alphas > 0) & np.isfinite(r) & ~blend, r, 0.0)  # both components must add light
        else:
            r = (a1 + alpha * a2) / np.sqrt(1 + 2 * alpha * c12 + alpha**2)
            alphas = np.full_like(r, alpha)
    i, j = np.unravel_index(int(np.argmax(r)), r.shape)
    if i in (0, len(lags) - 1) or j in (0, len(lags) - 1):
        raise ValueError("TODCOR peak at the edge of the velocity range: widen the range")
    # quadratic surface z = a + b x + c y + d x^2 + e xy + f y^2 through the 3x3 neighbourhood
    dx, dy = np.meshgrid([-1, 0, 1], [-1, 0, 1], indexing="ij")
    z = r[i - 1 : i + 2, j - 1 : j + 2].ravel()
    a_mat = np.column_stack([np.ones(9), dx.ravel(), dy.ravel(), dx.ravel() ** 2, (dx * dy).ravel(), dy.ravel() ** 2])
    q = np.linalg.lstsq(a_mat, z, rcond=None)[0]
    hess = np.array([[2 * q[3], q[4]], [q[4], 2 * q[5]]])
    try:
        off = -np.linalg.solve(hess, q[1:3])
    except np.linalg.LinAlgError:
        off = np.zeros(2)
    off = np.clip(off, -1, 1)
    peak = float(q[0] + q[1:3] @ off + 0.5 * off @ hess @ off)
    # independent pixels: the grid is finer than the spectrum's own pixels (v_step = half a pixel by default), and
    # counting the interpolated points as data made the errors sqrt(2) too small
    n = len(grid) * min(1.0, dln / float(np.median(np.diff(np.log(wave)))))
    # Zucker (2003) in two dimensions: covariance = -[N R''/R R^2 / (1 - R^2)]^-1 with the full Hessian, so the
    # error of each velocity includes its correlation with the other (blended lines); in grid steps^2
    try:
        cov = -np.linalg.inv(n * hess / peak * peak**2 / (1 - peak**2)) if 0 < peak < 1 else None
    except np.linalg.LinAlgError:
        cov = None

    shifts = np.array([lags[i] + off[0], lags[j] + off[1]]) * dln

    def err(k):
        if cov is None or not cov[k, k] > 0:
            return float("nan")
        return float(np.sqrt(cov[k, k]) * dln * C_KMS * np.exp(shifts[k]))  # d v / d shift = c e^shift

    a_best = float(alphas[i, j])
    out = {
        "rv1": float(v_from_ln(shifts[0])),
        "rv2": float(v_from_ln(shifts[1])),
        "rv1_err": err(0),
        "rv2_err": err(1),
        "peak": peak,
        "alpha": a_best,
        "flux_ratio": a_best * n1 / n2,  # f - 1 = A n1 g1 + B n2 g2 and alpha = B n2 / (A n1)
        "v": v_from_ln(lags * dln).tolist(),
    }
    same = np.array_equal(t1_wave, t2_wave) and np.array_equal(t1_flux, t2_flux)
    if same and a_best > 1:  # one template for both stars: (v1, v2, alpha) and (v2, v1, 1 / alpha) fit equally well
        # and noise chose, so the stars swapped between spectra (AI Phe); component 1 is the brighter one
        out |= {"rv1": out["rv2"], "rv2": out["rv1"], "rv1_err": out["rv2_err"], "rv2_err": out["rv1_err"]}
        out |= {"alpha": 1 / a_best, "flux_ratio": 1 / out["flux_ratio"]}
    return out
