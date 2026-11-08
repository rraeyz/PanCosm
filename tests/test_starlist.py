"""plans/photometry.md item 7: a star list saved on one night lands on the same stars on another night."""

import numpy as np
import pytest
from astropy.wcs import WCS

from astrowb.photometry.starlist import load_star_list, save_star_list


def wcs(crpix, angle_deg, scale=1.2 / 3600, flip=False):
    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crval = [31.0, 46.7]
    w.wcs.crpix = crpix
    a = np.radians(angle_deg)
    rot = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]]) * scale
    if flip:
        rot[0] *= -1
    w.wcs.cd = rot
    return w


def test_saved_on_one_night_lands_on_the_same_stars_on_another(tmp_path):
    night1, night2 = wcs([500, 400], 3.0), wcs([620, 350], 47.0, flip=True)  # moved, rotated, mirrored camera
    stars1 = [(510.2, 420.7), (300.4, 220.1), (700.9, 610.3), (480.0, 380.0)]
    path = save_star_list(
        tmp_path / "f.stars.json", stars1[0], stars1[1:3], [(stars1[3], "check")], (4, 10, 16), night1
    )
    got = load_star_list(path, night2, shape=(1000, 1200))
    sky = [night1.pixel_to_world_values(*xy) for xy in stars1]
    want = [night2.world_to_pixel_values(*s) for s in sky]
    found = [got["target"], *got["comps"], got["extras"][0][0]]
    assert np.max(np.abs(np.array(found) - np.array(want, float))) < 1e-6  # well within the plan's 1 px
    assert got["by"] == "sky" and got["radii"] == [4, 10, 16] and got["extras"][0][1] == "check"


def test_pixels_without_a_solution_and_stars_off_the_frame(tmp_path):
    path = save_star_list(tmp_path / "p.stars.json", (10, 10), [(20, 20), (5000, 5)])
    got = load_star_list(path, None, shape=(100, 100))
    assert got["by"] == "pixels" and got["target"] == (10.0, 10.0) and got["comps"] == [(20.0, 20.0)]
    assert got["outside"] == ["comparison 2"]
    bad = tmp_path / "x.json"
    bad.write_text("{}")
    with pytest.raises(ValueError):
        load_star_list(bad)
