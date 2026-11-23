"""VAR and DQ planes of a stack (plans/calibration.md CAL-16; the frames carry them from CAL-13).

VAR of a weighted mean over the frames kept at a pixel: sum(w_i^2 Var_i) / (sum w_i)^2, exact. Frames moved by a
shift are resampled with the same four bilinear weights as the data, the variance with their squares (exact); under a
rotation or scale the variance is interpolated with the data's kernel, an approximation. The median uses the
large-N approximation (pi / 2) x the variance of the mean (unweighted), also an approximation. A sum is the mean
times the number of frames. DQ: NODATA where no frame was kept, else only the bits set in EVERY kept frame (AND:
a cosmic ray rejected from one frame's pixel must not mark the stack).
"""

import numpy as np
from astropy.io import fits
from scipy.ndimage import map_coordinates

from ..core.planes import NODATA

NOTE = "VAR exact for shifts, approx. for rotation / median (pi/2 x mean)"


def available(paths):
    """(every frame has VAR, every frame has DQ) from the extension names."""
    have = []
    for p in paths:
        from ..io.lzw import readable

        with fits.open(readable(p)) as h:
            have.append({x.name for x in h})
    return all("VAR" in n for n in have), all("DQ" in n for n in have)


def warp(hdu, m, t, b0, b1, ny, nx, kind):
    """Rows b0..b1 of a plane under the data's transform: kind "var" (squared weights for a shift) or "dq" (nearest
    pixel); NaN where the frame does not cover."""
    from .stacking import _shifted_rows

    if np.array_equal(m, np.eye(2)):
        if kind == "dq":
            t = np.round(t)
        return _shifted_rows(hdu, b0, b1, t, ny, nx, 2 if kind == "var" else 1)
    yy, xx = np.meshgrid(np.arange(b0, b1, dtype=np.float64), np.arange(nx, dtype=np.float64), indexing="ij")
    xs, ys = m[0, 0] * xx + m[0, 1] * yy + t[0], m[1, 0] * xx + m[1, 1] * yy + t[1]
    lo, hi = max(int(np.floor(ys.min())) - 1, 0), min(int(np.ceil(ys.max())) + 2, ny)
    if hi <= lo:
        return np.full((b1 - b0, nx), np.nan, np.float32)
    sub = np.asarray(hdu.section[lo:hi, :], dtype=np.float32)
    return map_coordinates(sub, [ys - lo, xs], order=1 if kind == "var" else 0, cval=np.nan, prefilter=False)


def combine(keep, var, dq, weights, method):
    """(VAR, DQ) of one block from the kept mask (frames x rows x columns), the frames' variance (or None) and DQ
    (or None) blocks, the weights and the method."""
    w = np.ones(len(keep)) if weights is None or method == "median" else np.asarray(weights, float)
    wk = np.where(keep, w[:, None, None], 0.0)
    out_var = None
    if var is not None:
        with np.errstate(invalid="ignore", divide="ignore"):
            s = wk.sum(axis=0)
            out_var = (wk**2 * np.nan_to_num(var)).sum(axis=0) / s**2
        out_var = np.where(s > 0, out_var, np.nan)
        out_var = out_var * (np.pi / 2 if method == "median" else len(keep) ** 2 if method == "sum" else 1.0)
    bits = np.where(keep, np.nan_to_num(dq).astype(np.uint8) if dq is not None else 0, 255).astype(np.uint8)
    out_dq = np.bitwise_and.reduce(bits, axis=0)
    out_dq[~keep.any(axis=0)] = NODATA
    return (None if out_var is None else out_var.astype(np.float32)), out_dq
