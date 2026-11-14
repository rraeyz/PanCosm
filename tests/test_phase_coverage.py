"""PLN-8: the planner proposes only nights that fill the missing phases, best first; a period near one day is
flagged."""

import numpy as np
from astropy.coordinates import SkyCoord

from astrowb.planning import phase_coverage as pc
from astrowb.planning.visibility import Site

SITE = Site("TUG", 36.8242, 30.3356, 2500.0)


def test_only_the_missing_phases_are_proposed():
    t0, period = 2461000.30, 0.3172
    history = t0 + np.linspace(0, 0.4, 200) * period + 40 * period  # phases 0–0.4 observed
    have = pc.covered(history, t0, period, bins=40)
    assert have[:16].all() and not have[17:].any()
    coord = SkyCoord(31.04, 46.69, unit="deg")  # high in the November night sky at TUG
    plan = pc.windows(SITE, "2026-11-13", 5, coord, t0, period, have, min_alt=30.0)
    assert plan and all(w["new"] > 0 for w in plan)
    assert [w["new"] for w in plan] == sorted((w["new"] for w in plan), reverse=True)
    for w in plan:  # every proposed stretch reaches into 0.4–1.0
        ph = pc.phases(np.linspace(w["start"], w["end"], 50), t0, period)
        assert np.any(ph > 0.42)


def test_a_period_near_one_day_takes_weeks():
    assert pc.commensurability(1.0003) > 100  # weeks: nearly the same phases night after night
    assert pc.commensurability(0.3172) < 1
    assert pc.commensurability(0.5) == np.inf
