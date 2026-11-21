"""Write a FITS file so that the real name never holds half a file (plans/calibration.md CAL-14)."""

import os
from pathlib import Path

from astropy.io import fits


def write_fits(hdus, path, **kwargs):
    """hdus (an HDU or a list) is written to `<name>.part` beside path and renamed when complete; a `.part` left by an
    earlier crash is removed first, and ours too when the write fails."""
    path = Path(path)
    tmp = path.with_name(path.name + ".part")
    tmp.unlink(missing_ok=True)
    if not isinstance(hdus, fits.HDUList):
        hdus = fits.HDUList([hdus] if isinstance(hdus, fits.PrimaryHDU) else hdus)
    try:
        hdus.writeto(tmp, overwrite=True, **kwargs)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
