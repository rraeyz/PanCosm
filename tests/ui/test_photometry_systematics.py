"""PHO-31 on the Photometry page: the trends the field stars share are removed from the target, undoably."""

import numpy as np

from astrowb.ui.photometry_page import PhotometryPage
from astrowb.ui.photometry_systematics import fitted_signal


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


def _page(qtbot, n_stars, n=200):
    lc, trend, sine = _lc(n_stars, n)
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


def _whole(page, n_stars, seed=5):
    """A whole-field result (PHO-30) of n_stars stars that share the trend of _lc, on the light curve's frames."""
    _, trend, _ = _lc(2)
    rng = np.random.default_rng(seed)
    t = np.asarray(page.lc_raw["time"])
    mag = rng.uniform(0.2, 1.8, n_stars)[None, :] * trend[:, None] + rng.normal(0, 0.001, (len(t), n_stars))
    xy = np.column_stack([np.linspace(100, 900, n_stars), np.full(n_stars, 50.0)])
    xy[0] = page.target  # the target itself is in the field: it must be left out
    return {
        "field": {"time": t.tolist(), "xy": xy.tolist(), "mag": mag.tolist()},
        "variability": {"candidate": [False] * n_stars},
    }


def test_whole_field_is_the_field_when_it_exists(qtbot):
    page, _, sine = _page(qtbot, 5)  # too few comparison stars alone
    assert not page.field_box.isEnabled()
    page.field_source = lambda: _whole(page, 50)
    page._recompute()
    assert page.field_box.isEnabled()
    page.field_box.setChecked(True)
    assert page.light_curve["field_trends"]["stars"] == 49  # the target is out
    assert "whole-field" in page.field_note.text() and "49" in page.field_note.text()
    page.field_source = lambda: None  # no whole-field result: back to the comparison stars
    page._recompute()
    assert not page.field_box.isEnabled()


def test_tfa_keeps_the_sinusoid(qtbot):
    page, _, sine = _page(qtbot, 40, 1000)  # TFA's fit of 40 templates takes ~k/n of a signal's power: n large
    before = _rel(page)
    page.field_method.setCurrentIndex(2)
    page.field_box.setChecked(True)
    assert page.field_cfg[0] == "tfa"
    after = _rel(page)
    d = sine - sine.mean()
    amp = np.dot(after - after.mean(), d) / np.dot(d, d)
    assert abs(amp - 1) < 0.1 and np.std(after - after.mean() - d) < 0.5 * np.std(before - before.mean() - d)


def test_the_fitted_transit_model_is_kept_out_of_the_trends(qtbot):
    """The Timing and fit stage's model (its airmass trend divided out) is TFA's `fixed`: the signal keeps its size
    where the blind fit of 40 templates on 200 frames takes much of it."""
    page, _, sine = _page(qtbot, 40)
    page.field_method.setCurrentIndex(2)
    page.field_box.setChecked(True)
    d = sine - sine.mean()
    amp = lambda: np.dot(_rel(page) - _rel(page).mean(), d) / np.dot(d, d)  # noqa: E731
    blind = amp()
    airmass = np.linspace(1.2, 1.6, len(sine))
    z = (airmass - airmass.mean()) / airmass.std()
    model = 1.3 * 10 ** (-0.4 * sine) * np.exp(0.02 * z)  # baseline × signal × the fit's own airmass trend
    fit_lc = dict(page.light_curve) | {"airmass": airmass.tolist()}
    page.transit_fit = (fit_lc, {"model": model, "values": {"baseline": 1.3, "airmass": 0.02}})
    assert np.allclose(fitted_signal(page, page.light_curve), sine)
    page._recompute()
    assert abs(amp() - 1) < 0.05 < abs(blind - 1), (amp(), blind)
    assert "fitted transit is kept out" in page.field_note.text()
    page.transit_fit = (dict(fit_lc, time=[0.0] * len(sine)), page.transit_fit[1])  # another night's fit: unused
    page._recompute()
    assert "a 1 % dip would be reduced to" in page.field_note.text()


def test_a_variable_star_search_refreshes_the_controls_at_once(qtbot):
    from types import SimpleNamespace

    from astrowb.ui.area_pages import _found

    page, _, _ = _page(qtbot, 5)
    vf = SimpleNamespace(result=None)
    vf.show_result = lambda out: setattr(vf, "result", out)
    page.field_source = lambda: vf.result
    assert not page.field_box.isEnabled()
    _found(SimpleNamespace(photometry_page=page), vf, _whole(page, 50))
    assert page.field_box.isEnabled() and "49" not in page.field_note.text()  # enabled, nothing removed yet
