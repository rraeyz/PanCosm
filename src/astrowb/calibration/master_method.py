"""How a master is combined (plans/calibration.md CAL-5 item 2): the rejection each kind of frame wants, chosen
without thought. "auto": bias -> avsigclip (< 10 frames) else sigclip; dark -> sigclip high only (cosmic rays),
ccdclip high only when gain and read noise are known; flat -> minmax (< 5 frames) else sigclip, each frame already
scaled by its median. "as before": the clipped mean about the median with MAD scale (compute/combine.py)."""

import numpy as np
from astropy.io import fits

from ..hdr import get
from ..io.fits import find_image_hdu, inherited
from ..io.lzw import readable
from .combine import METHODS, _finish

CHOICES = ("auto", "as before", "sigclip", "avsigclip", "ccdclip", "crreject", "minmax", "pclip", "linear_fit",
           "gesd", "none")  # fmt: skip
DEFAULT = "auto"


def choose(kind, n, choice="auto", sigma=3.0, gain=0.0, read_noise=0.0):
    """(method, parameters, header text) of a master, or None for "as before"."""
    if choice == "as before":
        return None
    high_only = False
    if choice == "auto":
        if n < 3:
            choice = "none"  # nothing to tell a hit from the signal
        elif kind == "bias":
            choice = "avsigclip" if n < 10 else "sigclip"
        elif kind == "dark":
            choice, high_only = ("ccdclip" if gain > 0 and read_noise > 0 else "sigclip"), True
        else:
            choice = "minmax" if n < 5 else "sigclip"
    low = np.inf if high_only else sigma
    noise = {"gain": gain or 1.0, "read_noise": read_noise}
    both = {"lsigma": sigma, "hsigma": sigma}
    params = {"sigclip": {**both, "lsigma": low}, "avsigclip": both, "ccdclip": {**noise, **both, "lsigma": low},
              "crreject": {**noise, "hsigma": sigma}}.get(choice, {})  # fmt: skip
    text = f"{choice} {sigma:g} sigma{', high side only' if high_only else ''}, mean" if params else f"{choice}, mean"
    return choice, params, text


def from_settings(settings, camera):
    """The run parameters Settings and the camera profile decide: the master_combine choice and the profile's
    read noise (0: unknown)."""
    return {"master_combine": settings.get("calibration.master_combine", DEFAULT),
            "camera_read_noise": float(camera["read_noise"] or 0.0)}  # fmt: skip


def pick(kind, paths, params):
    """choose() for a run: the gain and read noise the frames' header gives (EGAIN is e-/ADU; GAIN is often a
    camera setting, so it is not used), else the run's own. A guessed number would clip good pixels."""
    with fits.open(readable(paths[0])) as hdul:
        header = inherited(hdul, find_image_hdu(hdul))
    gain = get(header, "EGAIN", default=0.0) or params.get("gain") or 0.0
    rn = get(header, "RDNOISE", "READNOIS", "READNOISE", default=0.0) or params.get("camera_read_noise") or 0.0
    return choose(
        kind, len(paths), params.get("master_combine", "auto"), params.get("sigma", 3.0), float(gain), float(rn)
    )


def combine_block(stack, how):
    """(image, frames kept, variance of the image σ² / N of the kept frames) of a block."""
    keep = METHODS[how[0]](stack, **how[1])
    image, count = _finish(stack, keep, 1)
    n = np.maximum(count, 2)
    with np.errstate(all="ignore"):
        spread = (keep * (stack - image) ** 2).sum(axis=0) / (n - 1)
    var = np.zeros(image.shape, np.float32) if len(stack) < 2 else np.nan_to_num(spread / n).astype(np.float32)
    return image, count, var
