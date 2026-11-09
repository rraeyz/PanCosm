"""PHO-29: difference imaging in a crowded field with changing seeing — a star varying by 5 % recovered, constant
stars flat near their photon limit."""

import numpy as np

from astrowb.photometry import dia


def render(xy, flux, sigma, shape, sky, rng=None, read_noise=5.0):
    ny, nx = shape
    yy, xx = np.indices(shape)
    img = np.full(shape, float(sky))
    for (x, y), f in zip(xy, flux, strict=True):
        x0, x1, y0, y1 = max(0, int(x) - 12), min(nx, int(x) + 13), max(0, int(y) - 12), min(ny, int(y) + 13)
        sl = (slice(y0, y1), slice(x0, x1))
        img[sl] += f / (2 * np.pi * sigma**2) * np.exp(-((xx[sl] - x) ** 2 + (yy[sl] - y) ** 2) / (2 * sigma**2))
    if rng is not None:
        img = rng.poisson(np.clip(img, 0, None)).astype(float) + rng.normal(0, read_noise, shape)
    return img


def test_a_varying_star_in_a_crowded_field():
    rng = np.random.default_rng(3)
    shape = (160, 160)
    n = 600  # crowded: a star every ~40 pixels, many blends
    xy = rng.uniform(8, 152, (n, 2))
    flux = 10 ** rng.uniform(3.0, 5.0, n)
    target = int(np.argmin(np.hypot(*(xy - 80).T)))
    flux[target] = 4e4
    ref_sigma = 1.2
    ref = render(xy, flux, ref_sigma, shape, 300.0)  # a noise-free reference (a stack of the best frames)
    psf = dia.gaussian_psf(2.3548 * ref_sigma)
    mask = dia.stamps(ref, n=30)
    changes, errors, truth = [], [], []
    for k, (sigma, scale, sky) in enumerate(
        ((1.5, 1.0, 310.0), (1.9, 0.9, 290.0), (1.7, 1.05, 330.0), (2.1, 0.95, 300.0))
    ):
        f = flux * scale
        amp = 1 + 0.05 * np.sin(k * 1.3 + 0.4)  # the target varies by up to 5 %
        f[target] *= amp
        frame = render(xy, f, sigma, shape, sky, rng)
        kernel, b = dia.solve_kernel(ref, frame, half=6, mask=mask)
        assert abs(kernel.sum() - scale) < 0.01  # the kernel's sum is the frame's scale (thin cloud)
        diff = dia.difference(ref, frame, kernel, b)
        var = np.clip(frame, 0, None) + 25.0
        d, e = dia.flux_changes(diff, xy, psf, kernel, var)
        changes.append(d / kernel.sum())  # in reference units
        errors.append(e / kernel.sum())
        truth.append(amp - 1)
    changes, errors = np.array(changes), np.array(errors)
    got = changes[:, target] / flux[target]
    assert np.all(np.abs(got - np.array(truth)) < 3 * errors[:, target] / flux[target] + 0.002)
    bright = np.flatnonzero((flux > 2e4) & (np.arange(n) != target))
    pull = changes[:, bright] / errors[:, bright]  # constant stars: their change in units of its error
    assert 0.4 < np.nanmedian(np.std(pull, axis=0, ddof=1)) < 1.3  # flat to about the photon limit
