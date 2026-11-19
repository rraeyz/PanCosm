"""The frame's variance and mask planes in photometry (plans/photometry.md PHO-36, calibration.md CAL-13): read
only from a file with our SCI / DQ / VAR layout, then the letters a star's aperture gets from the DQ bits and the
sky pixels the DQ bits rule out."""

import numpy as np

from ..core import planes

# letter -> DQ bits; a repaired cosmic ray is "C" only (its REPAIRED bit goes with it), REPAIRED without COSMIC is
# "R": the repaired value is measured and marked (PHO-36)
LETTERS = (("B", planes.BAD | planes.NODATA), ("S", planes.SATURATED), ("C", planes.COSMIC), ("T", planes.TRAIL),
           ("R", planes.REPAIRED))  # fmt: skip


def read(path):
    """(var, dq) of a file with a DQ or VAR extension, else None (only the header of a plain frame is looked at)."""
    from astropy.io import fits

    from ..io.lzw import readable

    with fits.open(readable(path)) as h:
        if not {"DQ", "VAR"} & {x.name for x in h}:
            return None
    f = planes.read(path)
    return f.var, f.dq


def sky_mask(dq):
    """True where a pixel may not enter a sky ring: any DQ bit except NONLINEAR."""
    return None if dq is None else (dq & ~np.uint8(planes.NONLINEAR)) != 0


def letters(dq, xy, r_ap):
    """One string per star: the letters of the DQ bits of the pixels whose centres lie inside its aperture."""
    ny, nx = dq.shape
    out = []
    for x, y in np.asarray(xy, float).reshape(-1, 2):
        if not (np.isfinite(x) and np.isfinite(y)):
            out.append("")
            continue
        y0, y1, x0, x1 = (
            max(int(y - r_ap), 0),
            min(int(y + r_ap) + 2, ny),
            max(int(x - r_ap), 0),
            min(int(x + r_ap) + 2, nx),
        )
        yy, xx = np.mgrid[y0:y1, x0:x1]
        bits = np.bitwise_or.reduce(dq[y0:y1, x0:x1][(xx - x) ** 2 + (yy - y) ** 2 <= r_ap * r_ap], initial=0)
        bits = int(bits) & ~(planes.REPAIRED if bits & planes.COSMIC else 0)
        out.append("".join(c for c, b in LETTERS if bits & b))
    return out


def merge(flags, extra):
    """The letters of two lists joined per star, each letter once."""
    return ["".join(dict.fromkeys(a + b)) for a, b in zip(flags, extra, strict=True)]
