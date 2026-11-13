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


def _exo_sample():
    from pathlib import Path

    return (Path(__file__).parent / "data" / "exoplanet_archive_sample.csv").read_text(encoding="utf-8")


def test_transiting_planets_from_a_recorded_archive_answer():
    """PLN-5: the Exoplanet Archive's transiting planets (a recorded answer, V < 11) in the finder's table; tonight's
    transits from Ankara come out whole, above the limit and in the dark."""
    from astrowb.planning.ephemerides import transiting_planets
    from astrowb.planning.finder import tonight_events
    from astrowb.planning.visibility import Site, night

    table = transiting_planets(fetch=lambda url: _exo_sample())
    assert len(table["name"]) > 500 and set(table["kind"]) == {"transit"}
    assert np.nanmax(table["duration"]) < 2 and np.nanmin(table["mag"]) > 0  # days, magnitudes
    site = Site("Ankara", 39.84, 32.78, 1250.0)
    events = tonight_events(table, site, "2026-11-14", min_alt=30, mag_range=(-5, 11))
    dusk, dawn = night(site, "2026-11-14")
    assert events and all(dusk.jd <= e["start"] and e["end"] <= dawn.jd for e in events)
    assert all(min(e["alt_start"], e["alt_mid"], e["alt_end"]) >= 30 for e in events)


def test_the_finder_window_adds_a_planet_with_its_ephemeris(qtbot):
    from PySide6.QtCore import QDate

    from astrowb.settings import Settings
    from astrowb.ui.plan_page import PlanPage

    page = PlanPage(Settings())
    qtbot.addWidget(page)
    page.site_name.setText("Ankara")
    page.lat.setValue(39.84)
    page.lon.setValue(32.78)
    page.min_alt.setValue(30)
    page.date.setDate(QDate(2026, 11, 14))
    asked = []
    dlg = page.finder_dialog(fetch=lambda url: asked.append(url) or _exo_sample())
    assert asked == []  # nothing asked until Fetch
    dlg.mag.setValue(11)
    dlg.fetch_button.click()
    qtbot.waitUntil(lambda: bool(dlg.events), timeout=30000)
    assert dlg.view.table.rowCount() == len(dlg.events)
    dlg.chosen = [0]
    (added,) = dlg.add_chosen()
    targets = page.targets()
    assert targets[-1]["name"] == added["name"] and abs(targets[-1]["period"] - added["period"]) < 1e-9
