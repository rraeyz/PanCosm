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
