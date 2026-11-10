"""A frame with its variance and data-quality planes (plans/calibration.md CAL-13; Astropy's CCDData, ccdproc's
propagation, the ERR / DQ extensions of ESO and HST).

    f = Frame.from_raw(raw, gain, read_noise, saturation)    variance from the photon and read noise, DQ bits set
    out = calibrate(f, bias, dark, k, flat)                  the variance carried through every step
    moved = shift(f, dx, dy)                                 a sub-pixel shift: data bilinear, variance with the
                                                             squared weights, DQ of every contributing pixel OR-ed
    write(path, f) / read(path)                              a FITS file with SCI, VAR, DQ extensions (a plain
                                                             FITS reads as a Frame without planes)
"""

from dataclasses import dataclass, field

import numpy as np

BAD, SATURATED, NONLINEAR, COSMIC, TRAIL, NODATA, REPAIRED, USER = 1, 2, 4, 8, 16, 32, 64, 128


@dataclass
class Frame:
    sci: np.ndarray
    var: np.ndarray | None = None
    dq: np.ndarray | None = None
    header: dict = field(default_factory=dict)

    @classmethod
    def from_raw(cls, raw, gain=1.0, read_noise=0.0, saturation=None, nonlinear=None, bias_level=0.0):
        """Variance (ADU²) = max(raw − bias, 0) / g + (RN / g)²; the saturated and non-linear pixels flagged."""
        raw = np.asarray(raw, np.float64)
        var = np.clip(raw - bias_level, 0, None) / gain + (read_noise / gain) ** 2
        dq = np.zeros(raw.shape, np.uint8)
        if saturation is not None:
            dq[raw >= saturation] |= SATURATED
        if nonlinear is not None:
            dq[raw >= nonlinear] |= NONLINEAR
        return cls(raw, var, dq)


def master(stack):
    """A master from a stack of frames (n, ny, nx): the mean and its variance σ² / N per pixel."""
    s = np.asarray(stack, np.float64)
    return Frame(s.mean(axis=0), s.var(axis=0, ddof=1) / len(s), np.zeros(s.shape[1:], np.uint8))


def calibrate(frame, bias=None, dark=None, k=1.0, flat=None):
    """(raw − bias − k·dark) / flat with the variances added (and the flat's relative error), the DQ planes OR-ed."""
    sci, var = frame.sci.copy(), frame.var.copy()
    dq = frame.dq.copy() if frame.dq is not None else np.zeros(sci.shape, np.uint8)
    for m, scale in ((bias, 1.0), (dark, k)):
        if m is not None:
            sci -= scale * m.sci
            var += scale**2 * m.var
            dq |= m.dq if m.dq is not None else 0
    if flat is not None:
        f = flat.sci / np.median(flat.sci)
        fv = flat.var / np.median(flat.sci) ** 2
        var = var / f**2 + sci**2 * fv / f**4
        sci = sci / f
        dq |= flat.dq if flat.dq is not None else 0
    return Frame(sci, var, dq, dict(frame.header))


def shift(frame, dx, dy):
    """The frame moved by (dx, dy) pixels: bilinear data, the variance with the squared weights (the pixels become
    correlated; the header notes the factor), the DQ of the four contributing pixels OR-ed, NODATA at the edges."""
    ny, nx = frame.sci.shape
    ix, iy = int(np.floor(dx)), int(np.floor(dy))
    fx, fy = dx - ix, dy - iy
    weights = {(0, 0): (1 - fx) * (1 - fy), (1, 0): fx * (1 - fy), (0, 1): (1 - fx) * fy, (1, 1): fx * fy}
    sci, var = np.zeros((ny, nx)), np.zeros((ny, nx))
    dq = np.zeros((ny, nx), np.uint8)
    covered = np.ones((ny, nx), bool)
    for (ox, oy), w in weights.items():
        src_x, src_y = np.arange(nx) - ix - ox, np.arange(ny) - iy - oy
        okx, oky = (src_x >= 0) & (src_x < nx), (src_y >= 0) & (src_y < ny)
        cx, cy = np.clip(src_x, 0, nx - 1), np.clip(src_y, 0, ny - 1)
        ok = oky[:, None] & okx[None, :]
        if w > 0:
            covered &= ok
            sci += w * frame.sci[np.ix_(cy, cx)]
            var += w * w * frame.var[np.ix_(cy, cx)]
            dq |= np.where(ok, frame.dq[np.ix_(cy, cx)], 0).astype(np.uint8)
    dq[~covered] |= NODATA
    header = dict(frame.header) | {"VARCORR": float(1 / sum(w * w for w in weights.values()))}
    return Frame(sci, var, dq, header)


def write(path, frame):
    from astropy.io import fits

    hdus = [fits.PrimaryHDU(), fits.ImageHDU(np.asarray(frame.sci, np.float32), name="SCI")]
    if frame.var is not None:
        hdus.append(fits.ImageHDU(np.asarray(frame.var, np.float32), name="VAR"))
    if frame.dq is not None:
        hdus.append(fits.ImageHDU(np.asarray(frame.dq, np.uint8), name="DQ"))
    for k, v in frame.header.items():
        hdus[0].header[k] = v
    fits.HDUList(hdus).writeto(path, overwrite=True)
    return path


def read(path):
    """A Frame from our SCI / VAR / DQ file, or from a plain FITS image (planes None)."""
    from astropy.io import fits

    with fits.open(path) as h:
        names = [x.name for x in h]
        if "SCI" in names:
            return Frame(np.asarray(h["SCI"].data, np.float64),
                         np.asarray(h["VAR"].data, np.float64) if "VAR" in names else None,
                         np.asarray(h["DQ"].data, np.uint8) if "DQ" in names else None, dict(h[0].header))  # fmt: skip
        return Frame(np.asarray(h[0].data, np.float64), None, None, dict(h[0].header))
