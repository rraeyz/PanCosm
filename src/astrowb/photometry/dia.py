"""Difference-image photometry for crowded fields (plans/photometry.md PHO-29).

A frame is matched by the reference image convolved with a kernel plus a sky difference; the stars that did not
change cancel, a star that did leaves its change, measured without its neighbours' light:

    frame ≈ reference ⊗ K + b        K: a (2h+1)² "delta basis" kernel, every pixel free (Bramich 2008, MNRAS 386,
                                      L77), solved by weighted least squares on stamps around bright stars
    D = frame − reference ⊗ K − b     the difference image
    δF = Σ D M / Σ M²,  M = (reference PSF) ⊗ K    the change of a star's flux in reference units, PSF-weighted

The kernel's sum is the frame's photometric scale against the reference (clouds, exposure); a star's flux on a frame
is (F_ref + δF) in reference units, so the light curve F_ref + δF needs no comparison stars — the kernel did that.
"""

import numpy as np
from scipy.signal import fftconvolve


def _shift(img, dy, dx):
    """out[y, x] = img[y − dy, x − dx] (zeros where it leaves the frame)."""
    out = np.zeros_like(img)
    ny, nx = img.shape
    out[max(dy, 0) : ny + min(dy, 0), max(dx, 0) : nx + min(dx, 0)] = img[
        max(-dy, 0) : ny + min(-dy, 0), max(-dx, 0) : nx + min(-dx, 0)
    ]
    return out


def stamps(ref, n=40, size=21, edge=None):
    """Boolean mask of the pixels used to solve the kernel: boxes around the n brightest peaks of the reference."""
    from scipy.ndimage import maximum_filter

    ref = np.asarray(ref, float)
    edge = size if edge is None else edge
    peaks = (ref == maximum_filter(ref, size=7)) & (ref > np.median(ref) + 5 * np.std(ref) / 3)
    ys, xs = np.nonzero(peaks)
    inside = (ys > edge) & (ys < ref.shape[0] - edge) & (xs > edge) & (xs < ref.shape[1] - edge)
    order = np.argsort(-ref[ys[inside], xs[inside]])[:n]
    mask = np.zeros(ref.shape, bool)
    half = size // 2
    for y, x in zip(ys[inside][order], xs[inside][order], strict=True):
        mask[y - half : y + half + 1, x - half : x + half + 1] = True
    return mask


def solve_kernel(ref, frame, half=5, mask=None, read_noise=5.0, gain=1.0, iterations=3):
    """(kernel (2h+1)², sky difference b) with frame ≈ ref ⊗ K + b, by weighted least squares over mask's pixels
    (all but the border when None), the weights from the frame's photon noise and refined by 4σ clipping."""
    ref, frame = np.asarray(ref, float), np.asarray(frame, float)
    ny, nx = ref.shape
    use = np.zeros(ref.shape, bool)
    use[half : ny - half, half : nx - half] = True
    if mask is not None:
        use &= mask
    offsets = [(dy, dx) for dy in range(-half, half + 1) for dx in range(-half, half + 1)]
    cols = np.array([_shift(ref, dy, dx)[use] for dy, dx in offsets] + [np.ones(use.sum())]).T
    y = frame[use]
    var = np.clip(y, 0, None) / gain + read_noise**2
    keep = np.ones(len(y), bool)
    for _ in range(iterations):
        sw = 1 / np.sqrt(var[keep])
        coef, *_ = np.linalg.lstsq(cols[keep] * sw[:, None], y[keep] * sw, rcond=None)
        res = (y - cols @ coef) / np.sqrt(var)
        new = np.abs(res) < 4 * max(1.0, float(np.std(res[keep])))  # a cosmic ray or a varying star in a stamp
        if np.array_equal(new, keep):
            break
        keep = new
    return coef[:-1].reshape(2 * half + 1, 2 * half + 1), float(coef[-1])


def convolve(ref, kernel):
    """ref ⊗ K as solve_kernel defines it (K[dy + h, dx + h] multiplies ref shifted by (dy, dx))."""
    return fftconvolve(np.asarray(ref, float), kernel, mode="same")


def difference(ref, frame, kernel, sky):
    return np.asarray(frame, float) - convolve(ref, kernel) - sky


def gaussian_psf(fwhm, half=None):
    """A normalised Gaussian PSF stamp of the reference's seeing."""
    s = fwhm / 2.3548
    half = half or int(np.ceil(3 * s)) + 1
    yy, xx = np.mgrid[-half : half + 1, -half : half + 1]
    g = np.exp(-(xx**2 + yy**2) / (2 * s * s))
    return g / g.sum()


def flux_changes(diff, xy, psf, kernel, var=None):
    """δF per star (reference flux units) and its error: the difference image fitted by the reference PSF
    convolved with the frame's kernel, centred on each star's (sub-pixel) position."""
    from scipy.ndimage import shift as subshift

    model = fftconvolve(psf, kernel, mode="full")
    h = model.shape[0] // 2
    out, err = [], []
    for x, y in np.atleast_2d(np.asarray(xy, float)):
        ix, iy = int(round(x)), int(round(y))
        m = subshift(model, (y - iy, x - ix), order=3, mode="constant")
        ys, xs = slice(iy - h, iy + h + 1), slice(ix - h, ix + h + 1)
        if iy - h < 0 or ix - h < 0 or iy + h + 1 > diff.shape[0] or ix + h + 1 > diff.shape[1]:
            out.append(np.nan)
            err.append(np.nan)
            continue
        d = diff[ys, xs]
        v = np.ones_like(d) if var is None else var[ys, xs]
        out.append(float(np.sum(d * m / v) / np.sum(m * m / v)))
        err.append(float(1 / np.sqrt(np.sum(m * m / v))))
    return np.array(out), np.array(err)
