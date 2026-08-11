"""Differential photometry: magnitudes from known comparison magnitudes, check stars, a variable comparison
star found and down-weighted, detrending; simulated series with known answers."""

import numpy as np
import pytest
from astropy.io import fits
from test_apertures import STARS, field

from astrowb.photometry import differential as d
from astrowb.photometry.lightcurve import light_curve

RNG = np.random.default_rng(4)
N = 300
T = np.linspace(0, 0.3, N)


def series(variable_comp=True):
    """Target with an eclipse, three comparison stars (the third varies when asked), photon-like noise."""
    true = {"t": 1 - 0.3 * np.exp(-0.5 * ((T - 0.15) / 0.02) ** 2)}
    comps = np.column_stack([np.full(N, 5e4), np.full(N, 3e4), np.full(N, 4e4)])
    if variable_comp:
        comps[:, 2] *= 1 + 0.05 * np.sin(2 * np.pi * T / 0.1)
    target = 4e4 * true["t"]
    noisy = lambda f: f + RNG.normal(0, np.sqrt(f))  # noqa: E731
    lc = {
        "time": T.tolist(),
        "target_flux": noisy(target).tolist(),
        "target_flux_err": np.sqrt(target).tolist(),
        "comp_flux": noisy(comps).tolist(),
        "comp_flux_err": np.sqrt(comps).tolist(),
    }
    rel, err = d.ensemble(lc["target_flux"], lc["target_flux_err"], lc["comp_flux"], lc["comp_flux_err"])
    return lc | {"rel_flux": rel.tolist(), "rel_flux_err": err.tolist()}, true


def test_delta_mag():
    dm, e = d.delta_mag([1.0, 10 ** (-0.4 * 0.5)], [0.01, 0.01])
    assert dm == pytest.approx([0.0, 0.5]) and e[0] == pytest.approx(1.0857 * 0.01, rel=1e-3)


def test_variable_comparison_star_is_found_and_down_weighted():
    lc, true = series()
    _, scatter = d.comps_against_others(lc["comp_flux"])
    assert np.argmax(scatter) == 2  # the others are disturbed too: the variable star is in their sum
    w = d.scatter_weights(lc["comp_flux"])
    assert w[2] < 0.05 * min(w[:2]) and w.sum() == pytest.approx(3)
    _, scatter = d.comps_against_others(lc["comp_flux"], w)
    assert scatter[2] > 4 * max(scatter[:2]) and max(scatter[:2]) < 0.009  # photon noise: 0.73 %
    plain = np.asarray(lc["rel_flux"])
    weighted, _ = d.ensemble(lc["target_flux"], lc["target_flux_err"], lc["comp_flux"], lc["comp_flux_err"], w)
    err = lambda r: np.std(r / np.median(r[:50]) - true["t"])  # noqa: E731
    assert err(weighted) < 0.6 * err(plain) and err(weighted) < 0.008  # down to the photon noise of the target


def test_magnitudes_from_known_comparison_magnitudes_and_check_star():
    zp = 25.0
    mags = np.array([11.2, 11.8, 11.5])
    comps = 10 ** (-0.4 * (mags - zp))
    target_mag, check_mag = 12.3, 11.9
    lc = {
        "time": T[:5].tolist(),
        "target_flux": [10 ** (-0.4 * (target_mag - zp))] * 5,
        "comp_flux": [comps.tolist()] * 5,
        "comp_flux_err": [(comps * 1e-3).tolist()] * 5,
    }
    rel, err = d.ensemble(lc["target_flux"], [1.0] * 5, lc["comp_flux"], lc["comp_flux_err"])
    lc |= {"rel_flux": rel.tolist(), "rel_flux_err": err.tolist()}
    out = d.star_magnitudes(lc, [11.2, None, 11.5])  # one comparison without a magnitude is skipped
    assert out["mag"] == pytest.approx([target_mag] * 5, abs=1e-6)
    check = d.star_magnitudes(lc, list(mags), flux=[10 ** (-0.4 * (check_mag - zp))] * 5, flux_err=[1.0] * 5)
    assert check["mag"] == pytest.approx([check_mag] * 5, abs=1e-6)


def test_detrend_removes_an_airmass_trend_outside_the_eclipse():
    lc, true = series(variable_comp=False)
    airmass = 1.1 + 2 * (T - 0.15) ** 2 * 10
    trended = np.asarray(lc["rel_flux"]) * np.exp(-0.08 * airmass)
    out = d.detrend(trended, {"airmass": airmass}, exclude=(0.08, 0.22), time=T)
    assert out["coefficients"]["airmass"] == pytest.approx(-0.08, abs=0.01)
    assert out["scatter_after"] < out["scatter_before"]
    flat = np.asarray(out["rel_flux"])
    flat = flat / np.median(flat[(T < 0.08) | (T > 0.22)])
    assert np.median(flat[np.abs(T - 0.15) < 0.003]) == pytest.approx(0.7, abs=0.01)  # the eclipse depth is kept
    assert np.std(flat - true["t"]) < 0.01  # what is left is photon noise
    with pytest.raises(ValueError):
        d.detrend(trended, {"airmass": airmass}, exclude=(-1, 1), time=T)
    # a real night (Qatar-1 b, LCO): a range that left only the first minutes outside carried the airmass trend
    # 100 times beyond the airmass it was fitted on, and the curve ran off to 2.8; now refused
    rising = 1.23 + 2.2 * (T - T.min())
    with pytest.raises(ValueError, match="airmass in the left-out range is far"):
        d.detrend(trended, {"airmass": rising}, exclude=(T.min() + 0.01, T.max() + 1), time=T)


def test_light_curve_measures_check_stars_and_flags_saturation(tmp_path):
    paths = []
    for i in range(3):
        img = field(4.0, seed=10 + i)
        h = fits.Header({"DATE-OBS": f"2026-11-15T20:{i:02d}:00", "EXPTIME": 30.0, "SATURATE": 3000.0})
        fits.PrimaryHDU(img.astype(np.float32), h).writeto(tmp_path / f"f{i}.fits")
        paths.append(tmp_path / f"f{i}.fits")
    xy = [s[:2] for s in STARS]
    lc = light_curve(paths, xy[0], xy[1:3], 6, 15, 20, extra_xy=[xy[3]])
    assert np.asarray(lc["extra_flux"]).shape == (3, 1) and np.asarray(lc["comp_flux_err"]).shape == (3, 2)
    check, _ = d.ensemble(
        np.asarray(lc["extra_flux"])[:, 0], np.asarray(lc["extra_flux_err"])[:, 0], lc["comp_flux"], lc["comp_flux_err"]
    )
    assert check / check.mean() == pytest.approx(np.ones(3), abs=0.02)  # a constant check star stays flat
    assert lc["saturation"] == 3000.0 and np.asarray(lc["peak"]).shape == (3, 4)
    assert max(lc["peak"][0]) > lc["saturation"]  # the brightest star (2.5e5 counts, FWHM 4) peaks above 3000
    cov = d.covariates(lc)
    assert {"time", "sky", "x", "y"} <= set(cov)


def synthetic_lc(n=60):
    t = np.linspace(2461000.3, 2461000.5, n)
    comps = np.column_stack([np.full(n, 5e4), np.full(n, 3e4)]) * (1 + RNG.normal(0, 0.002, (n, 2)))
    target = 4e4 * (1 - 0.3 * np.exp(-0.5 * ((t - 2461000.4) / 0.02) ** 2))
    extra = np.column_stack([np.full(n, 2e4), 1e4 * (1 + 0.1 * np.sin(t * 50))])  # K1 constant, T2 varies
    airmass = 1.2 + (t - 2461000.4) ** 2 * 30
    rel, err = d.ensemble(target, np.sqrt(target), comps, np.sqrt(comps))
    peak = np.full((n, 5), 1000.0)
    peak[5, 0] = 70000.0
    return {
        "file": ["f"] * n,
        "time": t.tolist(),
        "jd_utc": t.tolist(),
        "time_scale": "BJD_TDB",
        "rel_flux": rel.tolist(),
        "rel_flux_err": err.tolist(),
        "target_flux": target.tolist(),
        "target_flux_err": np.sqrt(target).tolist(),
        "comp_flux": comps.tolist(),
        "comp_flux_err": np.sqrt(comps).tolist(),
        "extra_flux": extra.tolist(),
        "extra_flux_err": np.sqrt(extra).tolist(),
        "airmass": airmass.tolist(),
        "sky": [[100.0] * 5] * n,
        "xy": [[[10.0, 10.0]] * 5] * n,
        "peak": peak.tolist(),
        "saturation": 65535.0,
    }


def test_photometry_page_differential_workflow(qtbot, tmp_path):
    from astrowb.photometry.export import aavso_extended
    from astrowb.ui.workspaces import PhotometryPage, export_csv

    page = PhotometryPage()
    qtbot.addWidget(page)
    page.viewer.set_image(field(4.0))
    page.images = ["x.fits"]
    for xy in ((60.3, 70.6), (140.2, 60.1), (100.7, 150.4)):
        page._clicked(*xy)
    page.click_role.setCurrentIndex(page.click_role.findData("check"))
    page._clicked(40.0, 160.0)
    page.click_role.setCurrentIndex(page.click_role.findData("target"))
    page._clicked(20.0, 20.0)
    names = [page.star_table.item(i, 0).text() for i in range(page.star_table.rowCount())]
    assert names == ["T1", "C1", "C2", "K1", "T2"]
    with qtbot.waitSignal(page.measure_requested) as sig:
        page._measure()
    assert sig.args[4]["extra_xy"] == [[40.0, 160.0], [20.0, 20.0]]
    page.show_light_curve(synthetic_lc())
    keys = [page.show_what.itemData(i) for i in range(page.show_what.count())]
    assert {"rel", "dmag", "mag", "extra0", "extra1", "comps", "all", "trends"} <= set(keys)
    assert "⚠ 1 frames" in page.result.text() and "K1: scatter" in page.result.text()
    page.star_table.item(1, 4).setText("11.20")  # typed-in comparison magnitudes
    page.star_table.item(2, 4).setText("11.75")
    lc = page.light_curve
    assert "mag" in lc and all("mag" in x for x in lc["extra"])
    zp = 11.20 + 2.5 * np.log10(np.asarray(lc["comp_flux"])[:, 0])
    assert lc["extra"][0]["mag"][0] == pytest.approx(zp[0] - 2.5 * np.log10(2e4), abs=0.01)
    page.weighted.setChecked(True)
    assert page.light_curve["weights"] is not None
    page.trend_boxes["airmass"].setChecked(True)
    page.exclude_from.setText("2461000.35")
    page.exclude_to.setText("2461000.45")
    page._detrend()
    assert "airmass" in page.light_curve["detrend"]["coefficients"]
    for i in range(page.show_what.count()):  # every view draws
        page.show_what.setCurrentIndex(i)
        assert page.plot.figure.axes
    out = tmp_path / "lc.csv"
    export_csv(page.light_curve, out)
    header = out.read_text(encoding="utf-8").splitlines()[0]
    assert "delta_mag" in header and "K1_rel_flux" in header and "T2_mag" in header and "V_mag" in header
    page._set_detrend(None)
    assert "detrend" not in page.light_curve
    report = aavso_extended(
        page.light_curve,
        "V1 Tst",
        "ABC",
        "V",
        [11.20, 11.75],
        check=page.light_curve["extra"][0]["rel_flux"],
        check_name="123",
    )
    row = report.splitlines()[-1].split(",")
    assert row[9] == "123" and float(row[10]) == pytest.approx(lc["extra"][0]["mag"][-1], abs=0.02)


def test_deleting_points_and_curve_spacing(qtbot, tmp_path):
    from types import SimpleNamespace

    from astrowb.ui.workspaces import PhotometryPage, PlotCanvas, export_csv

    page = PhotometryPage()
    qtbot.addWidget(page)
    page.viewer.set_image(field(4.0))
    page.images = ["x.fits"]
    for xy in ((60.3, 70.6), (140.2, 60.1), (100.7, 150.4)):
        page._clicked(*xy)
    page.click_role.setCurrentIndex(page.click_role.findData("check"))
    page._clicked(40.0, 160.0)
    lc = synthetic_lc(40)
    page.show_light_curve(lc)
    page.resize(1200, 800)
    page.show()
    page.plot.canvas.draw()
    t5 = lc["time"][5]
    page.delete_mode.setChecked(True)  # a click on point 5 deletes it
    ax, x, y = page._plotted
    px, py = ax.transData.transform((x[5], y[5]))
    page._plot_clicked(SimpleNamespace(inaxes=ax, x=px, y=py))  # on it: neighbours can be 2 px away (Windows dpi)
    assert len(page.light_curve["time"]) == 39 and t5 not in page.light_curve["time"]
    page._plot_clicked(SimpleNamespace(inaxes=ax, x=px + 500, y=py + 500))  # far from every point: nothing
    assert len(page.light_curve["time"]) == 39
    page.delete_point(0)
    assert len(page.light_curve["extra"][0]["rel_flux"]) == 38 and "deleted by hand" in page.result.text()
    export_csv(page.light_curve, tmp_path / "lc.csv")
    assert len((tmp_path / "lc.csv").read_text(encoding="utf-8").splitlines()) == 1 + 38
    page.restore_points()
    assert len(page.light_curve["time"]) == 40
    page.show_what.setCurrentIndex(page.show_what.findData("all"))
    page.spacing.setValue(0.0)  # curves on top of each other
    lines = page.plot.figure.axes[0].get_lines()
    assert [round(float(np.nanmedian(line.get_ydata())), 2) for line in lines] == [1.0, 1.0]
    page.spacing.setValue(0.2)
    lines = page.plot.figure.axes[0].get_lines()
    assert round(float(np.nanmedian(lines[1].get_ydata())), 2) == 0.8
    window = page.plot.open_window()  # a copy of the plot in its own window
    assert (
        window.findChild(PlotCanvas).figure.axes[0].get_lines()
        and window.findChild(PlotCanvas).figure is not page.plot.figure
    )
    window.close()


def test_photometry_page_sends_the_telescope_aperture_and_reports_scintillation(qtbot):
    from astrowb.ui.workspaces import PhotometryPage

    page = PhotometryPage()
    qtbot.addWidget(page)
    page.images = ["x.fits"]
    page._clicked(60.3, 70.6)
    page._clicked(140.2, 60.1)
    with qtbot.waitSignal(page.measure_requested) as sig:
        page._measure()
    assert "aperture_m" not in sig.args[4]  # 0: from the header
    page.telescope_d.setValue(0.4)
    with qtbot.waitSignal(page.measure_requested) as sig:
        page._measure()
    assert sig.args[4]["aperture_m"] == 0.4
    page.show_light_curve(synthetic_lc() | {"scintillation": [0.002] * 60, "aperture_m": 0.4})
    assert "Scintillation 2.2–2.2 mmag" in page.result.text()
    page.show_light_curve(synthetic_lc() | {"scintillation": None, "aperture_m": None})
    assert "Scintillation is not in the errors" in page.result.text()


def test_stars_marked_on_a_later_frame_are_carried_to_the_others(tmp_path, qtbot):
    """The owner marks the stars on whichever frame looks best: the field drifts 7 px over the series; positions
    marked on frame 3 give the same light curve as positions marked on frame 1, and the page shows every frame."""
    from astrowb.ui.workspaces import PhotometryPage

    paths, shift = [], [(0, 0), (2.5, 1.0), (5.0, 2.2), (7.1, 3.0)]
    for i, (dx, dy) in enumerate(shift):
        stars = [(x + dx, y + dy, f) for x, y, f in STARS]
        h = fits.Header({"DATE-OBS": f"2026-11-15T20:{i:02d}:00", "EXPTIME": 30.0})
        fits.PrimaryHDU(field(4.0, stars=stars, seed=20 + i).astype(np.float32), h).writeto(tmp_path / f"f{i}.fits")
        paths.append(str(tmp_path / f"f{i}.fits"))
    xy0 = [s[:2] for s in STARS]
    xy3 = [(x + 7.1, y + 3.0) for x, y in xy0]
    a = light_curve(paths, xy0[0], xy0[1:3], 6, 15, 20)
    b = light_curve(paths, xy3[0], xy3[1:3], 6, 15, 20, ref_path=paths[3])
    assert np.allclose(a["target_flux"], b["target_flux"], rtol=1e-6)  # the same apertures on every frame

    page = PhotometryPage()
    qtbot.addWidget(page)
    page.set_images(list(reversed(paths)))
    assert page.frame_slider.maximum() == 3 and "1 of 4" in page.frame_label.text()
    page.frame_slider.setValue(3)
    page._clicked(*xy3[0])
    page._clicked(*xy3[1])
    assert page.ref == 3 and page._series()[0] == paths[3]
    page.frame_slider.setValue(0)
    assert page.viewer.marker_list == [] and "frame 4" in page.frame_label.text()  # drawn on their own frame only
    page._clicked(*xy0[2])  # marking on another frame is refused, with the reason
    assert len(page.comps) == 1 and "frame 4" in page.result.text()
    page.use_frame.setChecked(False)  # frame 1 left out of the light curve
    assert paths[0] not in page._series() and "3 of them used" in page.images_label.text()
    sent = []
    page.measure_requested.connect(lambda *a: sent.append(a))
    page._measure()
    assert sent[0][0][0] == paths[3] and sent[0][4]["ref_image"] == paths[3]


def test_differential_view_first_and_the_way_on_to_the_fits(qtbot, tmp_path):
    """The default view is the classic differential plot (target below, comparison check above with its scatter);
    after a measurement the page says where the fits are and goes there."""
    from astrowb.settings import Settings
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    try:
        page = win.photometry_page
        page.target, page.comps = (10.0, 10.0), [(20.0, 20.0), (30.0, 30.0)]
        page.show_light_curve(synthetic_lc())
        assert page.show_what.currentData() == "diff" and page.next_box.isVisibleTo(page)
        ax = page.plot.figure.axes[0]
        labels = [t.get_text() for t in ax.get_legend().get_texts()]
        assert "T1 − comparison" in labels and any(t.startswith("C1 − C2") and "mmag" in t for t in labels)
        assert ax.yaxis_inverted()
        page._to_models(str(tmp_path / "lc.csv"))
        assert win.current_workspace() == "orbits" and win.models_page.file.text().endswith("lc.csv")
        assert (tmp_path / "lc.csv").read_text().count("\n") > 50
    finally:
        win.engine.shutdown()


def test_frame_list_quality_and_blink(tmp_path, qtbot):
    """Every frame in a list as in MaxIm DL: a row click shows it, unticking leaves it out, the quality numbers fill
    in with bad frames red and unticked (not deleted), blinking steps through the frames in use at the same zoom."""
    from PySide6.QtCore import Qt

    from astrowb.ui.workspaces import PhotometryPage

    paths = []
    for i in range(5):
        h = fits.Header({"DATE-OBS": f"2026-11-15T20:{i:02d}:00", "EXPTIME": 30.0})
        fits.PrimaryHDU(field(4.0, seed=40 + i).astype(np.float32), h).writeto(tmp_path / f"g{i}.fits")
        paths.append(str(tmp_path / f"g{i}.fits"))
    page = PhotometryPage()
    qtbot.addWidget(page)
    page.set_images(paths)
    t = page.frame_table
    assert t.rowCount() == 5 and t.item(2, 1).text() == "20:02:15"  # mid-exposure UTC
    t.setCurrentCell(3, 0)
    assert page.shown == 3 and "4 of 5" in page.frame_label.text()
    t.item(1, 0).setCheckState(Qt.Unchecked)
    assert paths[1] in page.skipped and "4 of them used" in page.images_label.text()
    rows = [{"file": p, "fwhm": 2.5, "stars": 30, "background": 300.0, "good": True, "why": []} for p in paths]
    rows[4] |= {"fwhm": 7.9, "good": False, "why": ["stars blurred"]}
    page.show_quality(rows)
    assert t.item(4, 2).text() == "7.90" and t.item(4, 0).foreground().color().name() == "#e5484d"
    page._drop_bad()
    assert t.item(4, 0).checkState() == Qt.Unchecked and len(page.images) == 5  # left out, not deleted
    page.viewer.zoom(3.0)
    zoom = page.viewer.transform().m11()
    page._blink_step()  # from frame 4 (index 3): the next used frame round the series is frame 1 (index 0)
    assert page.shown == 0 and page.viewer.transform().m11() == zoom
    page._blink_step()
    assert page.shown == 2  # frame 2 (index 1) is left out
