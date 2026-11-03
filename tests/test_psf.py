"""PHO-18: a close pair measured by PSF, and by apertures after the neighbour is removed."""

import numpy as np
import pytest

from astrowb.photometry import psf


def frame(seed=0, pair_ratio=3.0, fwhm=3.0, shape=(200, 200)):
    rng = np.random.default_rng(seed)
    yy, xx = np.indices(shape)
    s = fwhm / 2.3548
    img = np.full(shape, 200.0)
    jitter = rng.uniform(-0.5, 0.5, (25, 2))  # sub-pixel positions: the ePSF needs them to be sampled
    field = [(x + jitter[k, 0], y + jitter[k, 1], 30000.0)
             for k, (x, y) in enumerate((x, y) for x in range(25, 180, 38) for y in range(25, 180, 38))
             if (x, y) != (101, 101)]  # the pair stands there  # fmt: skip
    target = (100.3, 99.6, 20000.0)
    neighbour = (100.3 + 1.5 * fwhm, 99.6, 20000.0 * pair_ratio)
    for x, y, f in [*field, target, neighbour]:
        img += f / (2 * np.pi * s * s) * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * s * s))
    img = rng.poisson(img).astype(float)
    return img, field, target, neighbour


def aperture_flux(img, x, y, r=4.5, r_in=10, r_out=15):
    yy, xx = np.indices(img.shape)
    d = np.hypot(xx - x, yy - y)
    sky = np.median(img[(d >= r_in) & (d < r_out)])
    return float(np.sum(img[d < r] - sky))


def test_a_close_pair():
    img, field, target, neighbour = frame()
    keep = [i for i, (x, y, _f) in enumerate(field) if abs(x - 100) > 20 or abs(y - 100) > 20]
    xy = np.array([field[i][:2] for i in keep], float)
    chosen = psf.select_psf_stars(img, xy, [field[i][2] for i in keep], others=[target[:2], neighbour[:2]])
    assert len(chosen) >= 10
    epsf = psf.build_epsf(img, xy[chosen], oversampling=4)
    # differential photometry: the target against an isolated star measured the same way (the ePSF's own
    # normalisation, a couple of per cent, cancels)
    flux, err, table = psf.measure(img, epsf, [target[:2], xy[0]], 3.0, neighbours=[neighbour[:2]])
    assert flux[0] / flux[1] == pytest.approx(20000 / 30000, rel=0.01)
    plain = aperture_flux(img, *target[:2]) / aperture_flux(img, *xy[0])
    assert abs(plain / (2 / 3) - 1) > 0.10  # the neighbour spoils a plain aperture
    clean = psf.subtract(img, epsf, table, rows=[2])
    assert aperture_flux(clean, *target[:2]) / aperture_flux(clean, *xy[0]) == pytest.approx(2 / 3, rel=0.015)
    g_flux, _e, _t = psf.measure(img, psf.gaussian(3.0), [target[:2], xy[0]], 3.0, neighbours=[neighbour[:2]])
    assert g_flux[0] / g_flux[1] == pytest.approx(2 / 3, rel=0.02)
