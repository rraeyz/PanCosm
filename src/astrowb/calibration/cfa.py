"""Colour sensors in calibration (plans/calibration.md CAL-17).

flat = equalise(flat, "RGGB")     each colour's pixels of a mosaic flat scaled to one common median, so that a
                                  flat panel's colour does not tint every light (Siril's "equalise CFA")
rgb = debayer(image, "RGGB")      a bilinear colour picture — for looking at only; photometry uses the
                                  superpixel channels (io/bayer.split), which keep every count where it fell
"""

import numpy as np
from scipy import ndimage

from ..io.bayer import _phases


def equalise(flat, pattern):
    """The mosaic flat with every colour's pixels scaled to the median of all of them."""
    f = np.asarray(flat, np.float64).copy()
    h, w = f.shape[0] // 2 * 2, f.shape[1] // 2 * 2
    target = float(np.median(f[:h, :w]))
    for _colour, offs in _phases(pattern).items():
        planes = [f[dy:h:2, dx:w:2] for dy, dx in offs]
        level = float(np.median(np.concatenate([p.ravel() for p in planes])))
        for dy, dx in offs:
            f[dy:h:2, dx:w:2] *= target / level
    return f.astype(np.float32)


def debayer(image, pattern):
    """(ny, nx, 3) R, G, B by bilinear interpolation of each colour's samples (normalised convolution)."""
    a = np.asarray(image, np.float64)
    out = np.zeros((*a.shape, 3))
    kernel = np.array([[0.25, 0.5, 0.25], [0.5, 1.0, 0.5], [0.25, 0.5, 0.25]])
    for k, colour in enumerate("RGB"):
        mask = np.zeros(a.shape)
        for dy, dx in _phases(pattern).get(colour, []):
            mask[dy::2, dx::2] = 1.0
        num = ndimage.convolve(a * mask, kernel, mode="mirror")
        den = ndimage.convolve(mask, kernel, mode="mirror")
        out[..., k] = num / np.maximum(den, 1e-12)
    return out.astype(np.float32)
