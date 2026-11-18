"""Difference-image light curve (plans/photometry.md PHO-29): the reference from the sharpest frames, every frame
registered to it, then the kernel fit of photometry.dia."""

import numpy as np

from . import dia


def reference(paths, n_best):
    """(image, header): the n_best frames with the smallest FWHM (photometry.quality.measure, as the Frames tab),
    aligned on the first of them and combined by calibration.stacking.stack."""
    from ..calibration.stacking import stack
    from ..core.errors import AppError
    from . import quality

    fwhm = [(quality.measure(p)["fwhm"], str(p)) for p in paths]
    fwhm = sorted((f, p) for f, p in fwhm if f is not None)  # a frame with no measurable star cannot be the sharpest
    if not 1 <= n_best <= len(fwhm):
        raise AppError("n_best must be 1 to {n} (the frames with a measurable FWHM)", n=len(fwhm))
    best = [p for _, p in fwhm[:n_best]]
    image, _, header = stack(best, align="translation", rejection="sigma" if n_best >= 8 else "none")
    return np.asarray(image, float), header


def register(ref, frame):
    """The frame moved onto the reference (spline, shift from the stacking's phase correlation)."""
    from scipy.ndimage import shift

    from .aperture import frame_shift

    dx, dy = frame_shift(ref, frame)
    return shift(np.asarray(frame, float), (-dy, -dx), order=3, mode="nearest")


def light_curve(paths, ref, xy, fwhm, half=5, n_stamps=40, gain=1.0, read_noise=5.0):
    """Per frame: δF of every star (xy on the reference, (n, 2) x y) in reference counts with its error, and the
    kernel sum (the frame's scale). Returns (flux (frames, n), error (frames, n), scale (frames,)); the star's
    flux on a frame is F_ref + δF."""
    from ..calibration.masters import load

    ref = np.asarray(ref, float)
    mask, psf = dia.stamps(ref, n=n_stamps), dia.gaussian_psf(fwhm)
    flux, err, scale = [], [], []
    for p in paths:
        frame = register(ref, load(p)[0])
        kernel, sky = dia.solve_kernel(ref, frame, half=half, mask=mask, read_noise=read_noise, gain=gain)
        diff = dia.difference(ref, frame, kernel, sky)
        var = np.clip(frame, 0, None) / gain + read_noise**2
        d, e = dia.flux_changes(diff, xy, psf, kernel, var)
        flux.append(d / kernel.sum())  # kernel sum: the frame's scale, back to reference units
        err.append(e / kernel.sum())
        scale.append(float(kernel.sum()))
    return np.array(flux), np.array(err), np.array(scale)
