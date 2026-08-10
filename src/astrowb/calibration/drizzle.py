"""Drizzle (Fruchter & Hook 2002, PASP 114, 144): dithered, undersampled frames combined onto a finer grid.

Every input pixel is shrunk to a "drop" (pixfrac of its size) and laid on the output grid (scale times finer)
at its aligned position; each output pixel is the overlap-weighted mean of the drops that touch it, times s^2
(s = 1 / scale, the output pixel's size in input pixels; Fruchter & Hook eq. 3), so a star's counts are kept: the
sum over an aperture equals the frames' (checked on real LCO frames: 40 stars, 1.003 of the stack with this factor,
4.011 without it — photometry with the gain on a drizzled image needs counts). With
several sub-pixel dithers this recovers resolution that one frame cannot hold. Frames are aligned by the same
translation as stacking, so the overlaps separate into x and y: the whole frame is two sparse matrix products.

shortcut: translation only (as stacking); no per-pixel cosmic-ray rejection — calibrate with cosmic-ray
removal first, or give enough frames that one hit is diluted.
"""

import numpy as np


def _overlap(n_in, shift, scale, pixfrac, n_out):
    """Sparse (n_in x n_out) matrix: length of overlap of every input drop with every output pixel."""
    from scipy.sparse import coo_matrix

    centre = np.arange(n_in) - shift  # input pixel centres in reference-frame pixels
    lo, hi = (centre - pixfrac / 2 + 0.5) * scale, (centre + pixfrac / 2 + 0.5) * scale  # in output pixel units
    first = np.floor(lo).astype(int)
    rows, cols, vals = [], [], []
    for k in range(int(np.ceil(pixfrac * scale)) + 2):
        j = first + k
        a = np.minimum(hi, j + 1) - np.maximum(lo, j)
        ok = (a > 0) & (j >= 0) & (j < n_out)
        rows.append(np.flatnonzero(ok))
        cols.append(j[ok])
        vals.append(a[ok] / scale)  # back in input pixel units
    return coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n_in, n_out)).tocsr()


def drizzle(images, offsets, scale=2, pixfrac=0.6):
    """images: 2-D arrays (any iterable: frames can be read one at a time); offsets: (dx, dy) of each frame
    relative to the first (as align_offsets gives). Returns (image on the finer grid, weight map)."""
    images = iter(images)
    first = next(images)
    ny, nx = first.shape
    out_shape = (int(ny * scale), int(nx * scale))
    flux = np.zeros(out_shape)
    weight = np.zeros(out_shape)
    import itertools

    for img, (dx, dy) in zip(itertools.chain([first], images), offsets, strict=True):
        good = np.isfinite(img)
        data = np.where(good, img, 0.0)
        wy = _overlap(ny, dy, scale, pixfrac, out_shape[0])
        wx = _overlap(nx, dx, scale, pixfrac, out_shape[1])
        flux += wy.T @ (wx.T @ data.T).T  # Wy^T . data . Wx
        weight += wy.T @ (wx.T @ good.astype(float).T).T
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(weight > 0, flux / weight / scale**2, np.nan).astype(np.float32), weight.astype(np.float32)


def scaled_header(header, scale):
    """The WCS of the finer grid: pixel scale / scale, the same sky position at the same place."""
    h = header.copy()
    for i in (1, 2):
        if f"CRPIX{i}" in h:
            h[f"CRPIX{i}"] = (h[f"CRPIX{i}"] - 0.5) * scale + 0.5
        if f"CDELT{i}" in h:
            h[f"CDELT{i}"] /= scale
        for j in (1, 2):
            if f"CD{i}_{j}" in h:
                h[f"CD{i}_{j}"] /= scale
    for key in list(h.keys()):  # SIP distortion: polynomials in pixels from CRPIX, so A_p_q scales as scale^(1-p-q)
        parts = key.split("_")
        if len(parts) == 3 and parts[0] in ("A", "B", "AP", "BP") and parts[1].isdigit() and parts[2].isdigit():
            h[key] = h[key] * float(scale) ** (1 - int(parts[1]) - int(parts[2]))
    for key in ("NAXIS1", "NAXIS2"):
        h.pop(key, None)
    return h
