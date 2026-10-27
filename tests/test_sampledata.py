"""The practice night goes through the whole pipeline and gives back the minimum that was put in."""

import json

import pytest

from astrowb.engine import automation
from astrowb.engine.core import Engine
from astrowb.engine.tasks import TaskQueue


@pytest.mark.slow
def test_practice_night_end_to_end(tmp_path):
    q = TaskQueue(max_workers=2)
    try:
        eng = Engine(queue=q)
        truth = eng.run_step("sample.night", {"folder": str(tmp_path)}).result(120)["truth"]
        assert json.loads((tmp_path / "truth.json").read_text())["t_min_bjd_tdb"] == truth["t_min_bjd_tdb"]
        auto = automation.load(automation.TEMPLATES / "10-eclipsing-binary-night.json")
        out = automation.run(
            eng,
            auto,
            {"folder": str(tmp_path / "raw"), "output_dir": str(tmp_path / "cal"), "target_xy": truth["target_xy"]},
        )
    finally:
        q.shutdown()
    assert len(out["calibrated"]) == 48 and len(out["good"]) >= 44
    m = out["minimum"]
    assert m["time"] == pytest.approx(truth["t_min_bjd_tdb"], abs=1.5 / 1440)  # within 1.5 minutes


@pytest.mark.slow
def test_practice_transit_night_with_the_exoplanet_template(tmp_path):
    """ARC-21 / UI-8 task 2: the practice transit (1.2 %, 2.2 h) through the exoplanet template: mid-transit within
    3 minutes."""
    from astrowb import sampledata

    truth = sampledata.make(tmp_path, n_lights=120, transit=True)
    q = TaskQueue(max_workers=2)
    try:
        eng = Engine(queue=q)
        auto = automation.load(automation.TEMPLATES / "20-exoplanet-transit.json")
        inputs = {"folder": str(tmp_path / "raw"), "output_dir": str(tmp_path / "cal"), "target_xy": truth["target_xy"]}
        out = automation.run(eng, auto, inputs)
    finally:
        q.shutdown()
    assert out["minimum"]["time"] == pytest.approx(truth["t_min_bjd_tdb"], abs=3 / 1440)


def test_help_menu_makes_practice_data_and_opens_the_guide(qtbot, tmp_path):
    from astrowb.settings import Settings
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path / "s"))
    qtbot.addWidget(win)
    try:
        win.practice_data(str(tmp_path / "practice"))
        qtbot.waitUntil(lambda: win.current_workspace() == "guide", timeout=120000)
        assert (tmp_path / "practice" / "truth.json").exists()
        page = win.guide_page
        shown = [
            page.tree.topLevelItem(i).child(j).text(0)
            for i in range(page.tree.topLevelItemCount())
            for j in range(page.tree.topLevelItem(i).childCount())
            if not page.tree.topLevelItem(i).child(j).isHidden()
        ]
        assert "Your first night (practice data)" in shown
        assert "first-night-calibrate.png" in page.text.toMarkdown() or "image" in page.text.toHtml()
    finally:
        win.engine.shutdown()


def _minimum_offsets(tmp_path, nights):
    """Offsets of the timed minimum from the truth, and pulls (offset / reported error), over independent nights.

    The whole chain (scan, calibrate, light curve, BJD_TDB, Kwee-van Woerden) on 16 independent noisy nights:
    the mean offset from the true minimum is consistent with zero and the reported errors match the scatter
    (pull = offset / error has a spread near 1). Measured on 40 nights: +1.6 +- 1.3 s, pull spread 0.95."""
    import numpy as np

    from astrowb import sampledata
    from astrowb.engine import builtin  # noqa: F401
    from astrowb.engine.steps import execute

    class Ctx:
        def progress(self, *a):
            pass

        def check(self):
            pass

    offsets, pulls = [], []
    for seed in range(nights):
        d = tmp_path / str(seed)
        truth = sampledata.make(d, n_lights=48, seed=1000 + seed)
        frames = execute("calibration.scan", {"folder": str(d / "raw")}, {}, Ctx())["frames"]
        cal = execute("calibration.run", {"frames": frames, "output_dir": str(d / "cal")}, {}, Ctx())["calibrated"]
        stars = {"target_xy": truth["target_xy"], "comps_xy": truth["comps_xy"]}
        lc = execute("photometry.light_curve", {"images": cal} | stars, {}, Ctx())["light_curve"]
        m = execute("timeseries.minimum", {"light_curve": lc}, {"method": "kvw"}, Ctx())["minimum"]
        offsets.append((m["time"] - truth["t_min_bjd_tdb"]) * 86400)
        pulls.append(offsets[-1] / (m["error"] * 86400))
    return np.array(offsets), np.array(pulls)


@pytest.mark.slow
def test_minimum_times_are_unbiased_with_honest_errors(tmp_path):
    """16 nights: no bias and honest errors (the statistical check; measured on 40 nights: +1.6 +- 1.3 s, pull
    spread 0.95)."""
    import numpy as np

    offsets, pulls = _minimum_offsets(tmp_path, 16)
    assert abs(offsets.mean()) < 3 * offsets.std() / np.sqrt(len(offsets)) + 1.0  # no bias (seconds)
    assert 0.6 < pulls.std() < 1.5  # honest errors


def test_minimum_times_of_a_few_nights_are_close_to_the_truth(tmp_path):
    """The quick version for every run: 4 nights, each within 4 of its own reported errors of the true minimum."""
    import numpy as np

    _, pulls = _minimum_offsets(tmp_path, 4)
    assert np.all(np.abs(pulls) < 4)


def test_practice_exercises_find_their_answers(tmp_path):
    """ARC-21: the guide's "Try it" exercises, run by script, find the numbers the guide says."""
    import numpy as np

    from astrowb import sampledata
    from astrowb.engine import builtin  # noqa: F401  (registers the steps)
    from astrowb.engine.steps import execute

    class Ctx:
        def progress(self, *a):
            pass

        def check(self):
            pass

    sets = sampledata.practice_sets(tmp_path)
    data = np.loadtxt(sets["files"]["pulsator"], delimiter=",", skiprows=1)
    found = execute("timeseries.frequencies", {"time": data[:, 0].tolist(), "flux": data[:, 1].tolist()}, {}, Ctx())
    assert abs(found["frequencies"][0]["freq"] - 8.123) < 0.001  # Light curves → Frequency analysis: f1 = 8.123 c/d
    text = open(sets["files"]["minima"], encoding="utf-8").read()
    params = {"t0": sampledata.LTTE["t0"], "period": sampledata.LTTE["period"]}
    fit = execute("timeseries.oc_fit", {"minima": text}, params, Ctx())["fit"]
    assert abs(fit.p3 - 2900) < 100 and abs(fit.amplitude - 0.005) < 0.0005  # O−C → third body: about 2900 d
    rv = np.loadtxt(sets["files"]["sb2"], delimiter=",", skiprows=1)
    inputs = {"time": rv[:, 0].tolist(), "rv": rv[:, 1].tolist(), "rv2": rv[:, 2].tolist()}
    sb2 = execute("spectroscopy.orbit", inputs, {"period": 4.6}, Ctx())["orbit"]  # Spectroscopy → orbit, SB2
    assert abs(sb2["k"] - 62) < 1.5 and abs(sb2["k2"] - 91) < 1.5 and abs(sb2["q"] - 0.68) < 0.02
    from astrowb.spectroscopy import spectrum_io

    guesses = [list(g) for g in sampledata.SLIT["arc_lines"]]
    one_d = str(tmp_path / "slit_1d.fits")
    execute("spectroscopy.reduce", {"science": sets["files"]["slit_science"], "arc": sets["files"]["slit_arc"],
            "guesses": guesses, "output": one_d}, {"read_noise": 4.0}, Ctx())  # fmt: skip
    w, f, _, _ = spectrum_io.read(one_d)
    near = (w > 4852) & (w < 4872)
    depth = np.median(f[(w > 4830) & (w < 4895)]) - f[near]
    centre = np.sum(w[near] * depth) / np.sum(depth)  # the line's centroid (pixels are 1.75 Å)
    assert abs(centre - 4862.0) < 0.5  # Spectroscopy → Reduce: Hβ at 4862.0 Å (45 km/s away)
