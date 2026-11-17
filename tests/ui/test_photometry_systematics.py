"""PHO-31 on the Photometry page: the trends the field stars share are removed from the target, undoably."""

import numpy as np

from astrowb.ui.photometry_page import PhotometryPage


def _lc(n_stars, n=200, seed=3):
    rng = np.random.default_rng(seed)
    t = np.linspace(2461000.3, 2461000.5, n)
    trend = 0.05 * np.sin((t - t[0]) * 20) + 0.3 * (t - 2461000.4)  # magnitudes, shared (airmass, focus)
    sine = 0.01 * np.sin(2 * np.pi * (t - t[0]) / 0.05)  # the target's own signal, 1 % (1.09 % in flux terms)
    k = rng.uniform(0.2, 1.8, n_stars + 1)  # how strongly each star feels the trend
    k[0] = 2.5  # the target feels it more than the average star: differential photometry leaves some of it
    base = rng.uniform(2e4, 6e4, n_stars + 1)[:, None]
    mag = k[:, None] * trend + rng.normal(0, 0.001, (n_stars + 1, n))
    mag[0] += sine
    flux = base * 10 ** (-0.4 * mag)
    comps = flux[1:].T
    return {
        "file": ["f"] * n, "time": t.tolist(), "jd_utc": t.tolist(), "time_scale": "BJD_TDB",
        "target_flux": flux[0].tolist(), "target_flux_err": np.sqrt(flux[0]).tolist(),
        "comp_flux": comps.tolist(), "comp_flux_err": np.sqrt(comps).tolist(),
    }, trend, sine  # fmt: skip


def _page(qtbot, n_stars):
    lc, trend, sine = _lc(n_stars)
    page = PhotometryPage()
    qtbot.addWidget(page)
    page.target, page.comps = (10.0, 10.0), [(20.0 + i, 20.0) for i in range(n_stars)]
    page.show_light_curve(lc)
    return page, trend, sine


def _rel(page):
    return -2.5 * np.log10(np.asarray(page.light_curve["rel_flux"]))


def test_shared_trend_removed_and_signal_kept(qtbot):
    page, trend, sine = _page(qtbot, 40)
    assert page.field_box.isEnabled()
    before = _rel(page)
    page.field_box.setChecked(True)
    after = _rel(page)
    assert page.light_curve["field_trends"]["stars"] == 40
    resid = lambda y: np.std(y - y.mean() - (sine - sine.mean()))  # noqa: E731
    assert resid(after) < 0.2 * resid(before)  # the trend is gone
    amp = lambda y: np.dot(y - y.mean(), sine - sine.mean()) / np.dot(sine - sine.mean(), sine - sine.mean())  # noqa: E731
    assert abs(amp(after) - 1) < 0.1  # the sinusoid keeps its amplitude within 10 %
    assert "a 1 % dip would be reduced to" in page.field_note.text()
    page.undo_stack.undo()
    assert not page.field_box.isChecked() and np.allclose(_rel(page), before)
    page.undo_stack.redo()
    assert page.field_box.isChecked() and np.allclose(_rel(page), after)
    page.field_box.setChecked(False)  # unticking brings the original back
    assert np.allclose(_rel(page), before)


def test_fewer_than_thirty_stars_no_control(qtbot):
    page, _, _ = _page(qtbot, 20)
    assert not page.field_box.isEnabled()
    assert "30" in page.field_note.text()
