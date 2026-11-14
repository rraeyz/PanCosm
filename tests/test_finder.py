"""PLN-5: tonight's events from an ephemeris table — the same events the night planner finds, a VSX-sized table in
seconds."""

import time

import numpy as np

from astrowb.engine.steps import execute
from astrowb.planning.finder import tonight_events
from astrowb.planning.visibility import Site

SITE = Site("TUG", 36.8242, 30.3356, 2500.0)


class Ctx:
    def progress(self, *a):
        pass

    def check(self):
        pass


def table(n, seed=1):
    rng = np.random.default_rng(seed)
    return {
        "name": np.array([f"V{i}" for i in range(n)]),
        "ra": rng.uniform(0, 360, n),
        "dec": np.degrees(np.arcsin(rng.uniform(-1, 1, n))),
        "mag": rng.uniform(6, 18, n),
        "period": 10 ** rng.uniform(-1, 1.3, n),
        "t0": rng.uniform(2459000, 2460000, n),
        "duration": rng.uniform(0.04, 0.2, n),
        "kind": rng.choice(["EA", "EB", "EW", "transit"], n),
    }


def test_the_same_events_as_the_night_planner():
    t = table(60, seed=3)
    found = tonight_events(t, SITE, "2026-11-13", min_alt=25.0, secondary=False)
    assert found and all(e["alt_start"] >= 25 and e["alt_end"] >= 25 for e in found)
    names = sorted({e["name"] for e in found})[:4]
    rows = {str(n): i for i, n in enumerate(t["name"])}
    targets = [{"name": n, "ra": float(t["ra"][rows[n]]), "dec": float(t["dec"][rows[n]]),
                "t0": float(t["t0"][rows[n]]), "period": float(t["period"][rows[n]]),
                "duration": float(t["duration"][rows[n]])} for n in names]  # fmt: skip
    planned = execute("planning.night", {"site": {"name": "TUG", "lat": SITE.lat, "lon": SITE.lon,
                      "height": SITE.height}, "date": "2026-11-13", "targets": targets},
                      {"min_alt": 25.0, "step_min": 10.0}, Ctx())["night"]  # fmt: skip
    for target in planned["targets"]:
        full = [e["mid"] for e in target["events"] if e["full"] and e["kind"] == "primary"]
        mine = [e["mid"] for e in found if e["name"] == target["name"]]
        # the planner gives UTC wall-clock times (BJD → UTC: up to 8.3 min); the finder takes T0 as it is
        assert len(full) == len(mine) and np.allclose(sorted(full), sorted(mine), atol=9 / 1440)


def test_a_vsx_sized_table_in_seconds():
    t = table(40000, seed=5)
    start = time.perf_counter()
    found = tonight_events(t, SITE, "2026-11-13", min_alt=30.0, mag_range=(8, 15))
    took = time.perf_counter() - start
    assert len(found) > 100 and took < 15
    assert found[0]["score"] >= found[-1]["score"]
    assert all(8 <= e["mag"] <= 15 for e in found)
