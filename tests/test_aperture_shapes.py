"""PHO-22: a trailed star measured in an ellipse or a racetrack gives its untrailed copy's flux, with less noise
than the circle that holds the whole trail."""

import numpy as np
import pytest

from astrowb.photometry.aperture import measure
from astrowb.photometry.shapes import moments_shape

S, L, ANGLE, F, SKY = 1.5, 9.0, 30.0, 1e5, 100.0  # a 3 : 1 trail
SHAPE = (140, 140)
X0, Y0 = 70.3, 69.7


def star(length):
    yy, xx = np.indices(SHAPE)
    img = np.zeros(SHAPE)
    steps = np.linspace(-length / 2, length / 2, 400) if length else [0.0]
    for t in steps:
        cx, cy = X0 + t * np.cos(np.radians(ANGLE)), Y0 + t * np.sin(np.radians(ANGLE))
        img += F / len(steps) / (2 * np.pi * S * S) * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * S * S))
    return img + SKY


def test_trailed_star_in_an_ellipse_and_a_racetrack():
    r = 6.0
    point = measure(star(0), [(X0, Y0)], r, r + 8, r + 14)[0][0]
    trail = star(L)
    ratio, angle = moments_shape(trail - SKY, X0, Y0, 12)
    assert angle == pytest.approx(ANGLE, abs=0.5) and ratio < 0.6  # the shape read from the star itself
    ellipse = {"kind": "ellipse", "ratio": r / (L / 2 + r), "angle": angle}
    race = {"kind": "racetrack", "length": L, "angle": angle}
    a = L / 2 + r
    assert measure(trail, [(X0, Y0)], a, a + 6, a + 12, shape=ellipse)[0][0] == pytest.approx(point, rel=0.01)
    assert measure(trail, [(X0, Y0)], r, r + 6, r + 12, shape=race)[0][0] == pytest.approx(point, rel=0.005)
    noisy = trail + np.random.default_rng(0).normal(0, 10, SHAPE)
    e_circle = measure(noisy, [(X0, Y0)], a, a + 6, a + 12)[1][0]
    e_ellipse = measure(noisy, [(X0, Y0)], a, a + 6, a + 12, shape=ellipse)[1][0]
    e_race = measure(noisy, [(X0, Y0)], r, r + 6, r + 12, shape=race)[1][0]
    assert e_race < e_circle and e_ellipse < e_circle


def test_painted_pixels_and_the_circle_shape():
    img = star(0)
    mask = np.zeros(SHAPE, bool)
    mask[64:77, 64:77] = True
    flux = measure(img, [(X0, Y0)], 6, 14, 20, shape={"kind": "pixels", "mask": [mask]})[0][0]
    assert flux == pytest.approx((img[mask] - SKY).sum(), rel=1e-9)
    assert (
        measure(img, [(X0, Y0)], 6, 14, 20, shape={"kind": "circle"})[0][0] == measure(img, [(X0, Y0)], 6, 14, 20)[0][0]
    )


def test_a_night_of_trailed_frames_through_the_light_curve(tmp_path):
    """The racetrack goes through the whole run (photometry.light_curve's aperture_shape): a constant target against
    three comparison stars on trailed frames comes out flat, with less scatter than circles holding the trails."""
    from astropy.io import fits

    from astrowb.engine.steps import execute

    rng = np.random.default_rng(4)
    yy, xx = np.indices((160, 200))
    stars = [(60.3, 70.2, 6e4), (130.7, 50.1, 8e4), (150.2, 120.4, 5e4), (40.9, 120.8, 7e4)]
    paths = []
    for i in range(12):
        img = np.full((160, 200), 300.0)
        for x0, y0, f in stars:
            for t in np.linspace(-L / 2, L / 2, 60):
                cx, cy = x0 + t * np.cos(np.radians(ANGLE)), y0 + t * np.sin(np.radians(ANGLE))
                img += f / 60 / (2 * np.pi * S * S) * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * S * S))
        img = rng.poisson(img).astype(np.float32)
        h = fits.Header({"DATE-OBS": f"2026-11-14T20:{i:02d}:00", "EXPTIME": 60.0})
        fits.PrimaryHDU(img, h).writeto(tmp_path / f"f{i:02d}.fits")
        paths.append(str(tmp_path / f"f{i:02d}.fits"))
    inputs = {"images": paths, "target_xy": stars[0][:2], "comps_xy": [s[:2] for s in stars[1:]]}
    race = {"kind": "racetrack", "length": L, "angle": ANGLE}

    def scatter(params):
        lc = execute("photometry.light_curve", inputs, params, None)["light_curve"]
        rel = np.asarray(lc["rel_flux"])
        return np.std(rel / rel.mean()), np.median(np.asarray(lc["rel_flux_err"]) / rel)

    a = L / 2 + 6
    circle, _ = scatter({"r_ap": a, "r_in": a + 6, "r_out": a + 12})
    track, expected = scatter({"r_ap": 6.0, "r_in": 12.0, "r_out": 18.0, "aperture_shape": race})
    assert track < circle and track < 1.6 * expected  # flat to its errors
