"""Frame streams from FITS cubes (PHO-38): frames and per-frame times, without a FITS file per frame.

Times are seconds from the cube's start time (timing.start_time: DATE-OBS ...) to the START of each frame. The repo
handles no per-frame cadence keyword, so the cadence (seconds between frame starts) is an explicit argument.
SER is not read: its header layout is not written down in the repo.
"""

import numpy as np
from astropy.io import fits

from .. import timing
from .fits import find_image_hdu


def read_cube(path, cadence: float):
    """(frames[n, y, x] float32, seconds[n], start ISO UTC) of a FITS cube (3-D primary or image HDU)."""
    if not cadence > 0:
        raise ValueError("the cadence (seconds between frames) must be positive")
    with fits.open(path) as hdul:
        hdu = hdul[find_image_hdu(hdul)]
        if hdu.header.get("NAXIS") != 3:
            raise ValueError("not a cube: expected 3 axes (frames, rows, columns)")
        frames = np.asarray(hdu.data, dtype=np.float32)
        start = timing.start_time(hdu.header)
    return frames, np.arange(len(frames)) * float(cadence), start.utc.isot
