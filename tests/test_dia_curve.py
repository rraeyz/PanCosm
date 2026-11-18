"""PHO-29: reference from the sharpest frames, registration, and a variable star in a crowded field."""

import numpy as np
from astropy.io import fits
from test_dia import render

from astrowb.photometry import dia_curve


def test_reference_from_sharpest_and_variable_star_with_shifts(tmp_path):
    rng = np.random.default_rng(7)
    shape = (140, 140)
    n = 250
    xy = rng.uniform(15, 125, (n, 2))
    flux = 10 ** rng.uniform(3.0, 4.8, n)
    target = int(np.argmin(np.hypot(*(xy - 70).T)))
    flux[target] = 4e4
    seeing = [1.1, 1.2, 1.15, 1.2, 1.6, 1.9, 2.1, 1.7, 1.5, 1.8, 1.9, 2.0]  # sigma, px; the first four sharpest
    shifts = [(0, 0), (3, -2), (0.4, 0.7), (-5, 4), (1.5, 2.5), (-0.3, -0.6), (6, 1), (2.2, -3.1), (0, 2), (-2, -2),
              (4.5, 0.5), (-1.2, 3.3)]  # fmt: skip
    amps = 1 + 0.06 * np.sin(np.arange(len(seeing)) * 0.9)
    paths = []
    for k, (s, (dx, dy)) in enumerate(zip(seeing, shifts, strict=True)):
        f = flux.copy()
        f[target] *= amps[k]
        img = render(xy + [dx, dy], f, s, shape, 300.0, rng)
        p = tmp_path / f"f{k:02d}.fits"
        fits.PrimaryHDU(img.astype(np.float32), fits.Header({"EXPTIME": 30.0})).writeto(p)
        paths.append(str(p))
    ref, header = dia_curve.reference(paths, 4)
    assert header["EXPTIME"] == 30.0
    # the reference is as sharp as the four best frames, not the night's average
    assert dia_curve.reference(paths[4:], 4)[0].max() < ref.max()
    sigma_ref = 1.2
    got, err, scale = dia_curve.light_curve(paths, ref, xy, 2.3548 * sigma_ref)
    # positions are those of frame 0 (the stack's base)
    truth = (amps - amps[:4].mean()) * flux[target]  # the reference holds the mean of the four
    assert np.all(np.abs(got[:, target] - truth) < 4 * err[:, target] + 0.004 * flux[target])
    assert np.all(np.abs(scale - 1) < 0.02)
