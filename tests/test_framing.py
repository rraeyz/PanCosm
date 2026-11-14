"""PLN-6: the suggested framing keeps more rule-passing comparison stars than the target-centred one."""

import numpy as np
import pytest

from astrowb.planning import framing

NYVIR = (204.70, -2.03)


def test_a_field_whose_comparison_stars_sit_to_one_side():
    rng = np.random.default_rng(2)
    # eight good comparison stars 9–14′ east of NY Vir, a 20′ × 14′ sensor: centred, most fall off the edge
    ra = NYVIR[0] + rng.uniform(9, 14, 8) / 60 / np.cos(np.radians(NYVIR[1]))
    dec = NYVIR[1] + rng.uniform(-4, 4, 8) / 60
    stars = np.column_stack([ra, dec, np.ones(8)])
    best = framing.suggest(NYVIR, stars, fov=(20.0, 14.0), margin=1.0)
    assert best["centred_kept"] < 6 <= best["kept"]  # as the plan asks: ≥ 6 where centred keeps fewer
    assert best["offset"][0] > 0  # the pointing moves east, towards the stars
    x, y = framing._plane(*best["centre"], *NYVIR)
    assert framing.inside(0.0, 0.0, (x, y), best["angle"], (20.0, 14.0), 1.0)  # NY Vir still well inside


def test_turning_the_camera_helps_a_line_of_stars():
    # stars along a north–south line 10′ long: a 20′ × 8′ sensor must turn to hold them
    dec = NYVIR[1] + np.linspace(-6, 6, 7) / 60
    stars = np.column_stack([np.full(7, NYVIR[0]), dec, np.ones(7)])
    flat = framing.suggest(NYVIR, stars, fov=(20.0, 8.0), margin=0.5)
    turned = framing.suggest(NYVIR, stars, fov=(20.0, 8.0), margin=0.5, angles=(0.0, 90.0))
    assert turned["kept"] == 7 > flat["kept"] and turned["angle"] == 90.0


def test_a_target_that_cannot_fit():
    with pytest.raises(ValueError):
        framing.suggest(NYVIR, [], fov=(2.0, 2.0), margin=1.5)


@pytest.mark.parametrize("dec", [10.0, 85.0])
def test_a_mosaic_overlaps_as_asked_even_near_the_pole(dec):
    w, h = 30.0, 20.0
    panels = framing.mosaic((120.0, dec), 2, 3, (w, h), overlap=0.15)
    assert len(panels) == 6
    turns = max(abs(p["angle"]) for p in panels)
    assert (turns > 1.0) if dec > 80 else (turns < 0.2)  # near the pole the camera turns panel by panel
    by = {(p["row"], p["col"]): p for p in panels}
    for (r, c), p in by.items():
        for dr, dc, along, size in ((0, 1, 0, w), (1, 0, 1, h)):
            q = by.get((r + dr, c + dc))
            if q is None:
                continue
            x, y = framing._plane(q["ra"], q["dec"], p["ra"], p["dec"])  # the neighbour in this panel's own plane
            a = np.radians(p["angle"])
            u, v = x * np.cos(a) + y * np.sin(a), -x * np.sin(a) + y * np.cos(a)
            step = (u, v)[along]
            assert step == pytest.approx(size * 0.85, rel=0.01)  # 15 % overlap within 1 %
            assert abs((v, u)[along]) < 0.01 * size  # and not slid sideways
