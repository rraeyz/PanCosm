"""Bad pixels as files and the choice of what to do with them (plans/calibration.md CAL-8; IRAF fixpix / ccdmask,
ccdproc, Siril's cosmetic correction).

    mask = from_masters(dark, flat)          hot (dark), dead / low (flat), and whole bad columns and rows
    mask |= read(path, shape)                a FITS mask image (non-zero = bad) or IRAF text regions "x1 x2 y1 y2"
    write(path, mask)                        the same two formats (by the file's extension: .fits or .txt)
    out = repair(data, mask, mode)           "none" (flag only: right for photometry, which flags its apertures),
                                             "neighbours" (median of good neighbours), "columns" (along the row)
"""

from pathlib import Path

import numpy as np

from . import masters


def bad_lines(image, nsigma=5.0):
    """Whole columns and rows that stand apart: their median off the median of the lines by nsigma robust σ."""
    img = np.asarray(image, float)
    mask = np.zeros(img.shape, bool)
    for axis in (0, 1):  # 0: columns (median down each), 1: rows
        prof = np.nanmedian(img, axis=axis)
        med = np.median(prof)
        sigma = 1.4826 * np.median(np.abs(prof - med))
        bad = np.abs(prof - med) > nsigma * max(sigma, 1e-9)
        if axis == 0:
            mask[:, bad] = True
        else:
            mask[bad, :] = True
    return mask


def from_masters(dark=None, flat=None, hot_sigma=masters.HOT_SIGMA, cold_level=masters.COLD_LEVEL):
    """The defect map of the masters (masters.defect_map) with the bad columns and rows of either."""
    mask = masters.defect_map(dark, flat, hot_sigma, cold_level)
    for image in (dark, flat):
        if image is not None:
            mask |= bad_lines(image)
    return mask


def read(path, shape):
    """A mask from a file: a FITS image of the frame's size (non-zero = bad) or IRAF text regions, one
    "x1 x2 y1 y2" per line (1-based, inclusive; # comments)."""
    path = Path(path)
    if path.suffix.lower() in (".fits", ".fit", ".fts"):
        from astropy.io import fits

        data = fits.getdata(path)
        if data.shape != tuple(shape):
            raise ValueError(f"the mask is {data.shape[1]} × {data.shape[0]} px, the frames {shape[1]} × {shape[0]}")
        return np.asarray(data) != 0
    mask = np.zeros(shape, bool)
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split("#")[0].split()
        if len(parts) < 4:
            continue
        x1, x2, y1, y2 = (int(float(v)) for v in parts[:4])
        mask[max(0, y1 - 1) : y2, max(0, x1 - 1) : x2] = True
    return mask


def _runs(mask):
    """IRAF regions covering mask: whole columns first, then runs along each row."""
    ny, nx = mask.shape
    lines, left = [], mask.copy()
    for x in np.flatnonzero(mask.all(axis=0)):
        lines.append((x + 1, x + 1, 1, ny))
        left[:, x] = False
    for y in range(ny):
        row = np.flatnonzero(np.diff(np.r_[0, left[y].astype(int), 0]))
        for a, b in zip(row[0::2], row[1::2], strict=True):
            lines.append((a + 1, b, y + 1, y + 1))
    return lines


def write(path, mask):
    path = Path(path)
    if path.suffix.lower() in (".fits", ".fit", ".fts"):
        from astropy.io import fits

        fits.PrimaryHDU(np.asarray(mask, np.uint8), fits.Header({"NBAD": int(np.sum(mask))})).writeto(
            path, overwrite=True
        )
    else:
        text = "# bad pixels: x1 x2 y1 y2 (1-based, inclusive)\n" + "".join(
            f"{a} {b} {c} {d}\n" for a, b, c, d in _runs(mask)
        )
        path.write_text(text, encoding="utf-8")
    return path


def repair(data, mask, mode="neighbours"):
    """The data with the bad pixels repaired by mode ("none" returns the data untouched)."""
    if mode == "none":
        return np.asarray(data)
    if mode == "neighbours":
        return masters.repair(data, mask)
    if mode == "columns":  # linear along each row between the nearest good pixels
        out = np.asarray(data, np.float32).copy()
        x = np.arange(out.shape[1])
        for y in np.flatnonzero(mask.any(axis=1)):
            good = ~mask[y]
            if good.sum() >= 2:
                out[y, ~good] = np.interp(x[~good], x[good], out[y, good])
        return out
    raise ValueError(f"unknown repair: {mode}")
