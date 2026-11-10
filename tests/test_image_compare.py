"""IMG-13: a new star of magnitude 16 in tonight's frame is obvious in the difference with the older frame, and
"what is this?" finds nothing known there while a neighbouring catalogue star is named."""

import numpy as np
from astropy.wcs import WCS

from astrowb.io import compare

SHAPE = (200, 240)


def field(rng, stars, shift=(0.0, 0.0), scale=1.0, sky=500.0, sigma=1.7):
    yy, xx = np.indices(SHAPE)
    img = np.full(SHAPE, sky)
    for x, y, f in stars:
        x, y = x + shift[0], y + shift[1]
        img += scale * f / (2 * np.pi * sigma**2) * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * sigma**2))
    return img + rng.normal(0, 6, SHAPE)


def test_a_new_star_and_what_it_is():
    rng = np.random.default_rng(7)
    stars = [(float(x), float(y), float(10 ** (0.4 * (25 - m)))) for x, y, m in
             zip(rng.uniform(20, 220, 60), rng.uniform(20, 180, 60), rng.uniform(13, 18, 60), strict=True)]  # fmt: skip
    old = field(rng, stars, sky=420.0)
    nova = (131.0, 77.0, 10 ** (0.4 * (25 - 16)))
    new = field(rng, [*stars, nova], shift=(2.3, -1.6), scale=0.85)  # pointed a little off, thinner cloud
    d = compare.difference(new, old)
    assert abs(d["shift"][0] - 2.3) < 0.1 and abs(d["shift"][1] + 1.6) < 0.1 and abs(d["scale"] - 0.85) < 0.03
    found = compare.new_sources(d["image"])
    x, y, sig = found[0]
    assert np.hypot(x - (nova[0] + 2.3), y - (nova[1] - 1.6)) < 1.0 and sig > 20
    assert len(found) <= 3  # hardly anything else stands out
    w = WCS(naxis=2)
    w.wcs.ctype, w.wcs.crval, w.wcs.crpix = ["RA---TAN", "DEC--TAN"], [150.0, 20.0], [120, 100]
    w.wcs.cdelt = [-1 / 3600, 1 / 3600]
    ras, decs = w.pixel_to_world_values([s[0] + 2.3 for s in stars], [s[1] - 1.6 for s in stars])
    rows = [
        {"name": f"Gaia {i}", "ra": float(r), "dec": float(dd)} for i, (r, dd) in enumerate(zip(ras, decs, strict=True))
    ]
    at_nova = w.pixel_to_world_values(x, y)
    assert compare.what_is(at_nova, rows, 2.0) == []
    near = compare.what_is(w.pixel_to_world_values(stars[0][0] + 2.3, stars[0][1] - 1.6), rows, 2.0)
    assert near and near[0]["name"] == "Gaia 0"
