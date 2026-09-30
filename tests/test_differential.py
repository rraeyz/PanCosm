"""Differential photometry: magnitudes from known comparison magnitudes, check stars, a variable comparison
star found and down-weighted, detrending; simulated series with known answers."""

import numpy as np
import pytest
from astropy.io import fits
from PySide6.QtCore import Qt
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
        assert page.show_what.currentData() == "diff" and not page.next_box.isHidden()
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


def test_no_magnitude_where_the_flux_ratio_is_not_positive():
    """A frame where the target's flux (after the sky) is zero or negative has no magnitude: NaN for both, not a
    negative error, which the light-curve plot refused (the owner's NSVS 07826147 night: "'yerr' must not contain
    negative values")."""
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib.figure import Figure

    m, e = d.delta_mag([1.0, -0.2, 0.0, 0.5], [0.01, 0.01, 0.01, 0.01])
    assert np.isfinite(m[[0, 3]]).all() and np.isnan(m[[1, 2]]).all() and np.isnan(e[[1, 2]]).all()
    assert (e[[0, 3]] > 0).all()
    Figure().subplots().errorbar(np.arange(4), m, e)  # raised ValueError


def test_photometry_page_draws_a_light_curve_with_frames_that_lost_the_target(qtbot, tmp_path):
    """The owner's NY Vir night: frames where the target's flux after the sky is negative made the page fail with
    "'yerr' must not contain negative values" instead of drawing the light curve. Now it is drawn, and those frames
    are named on the plot so they can be left out."""
    from astrowb.ui.workspaces import PhotometryPage

    page = PhotometryPage()
    qtbot.addWidget(page)
    lc = synthetic_lc()
    lc["file"] = [f"frame_{i:03d}.fits" for i in range(60)]
    for i in (7, 31):
        lc["target_flux"][i] = -500.0
        lc["rel_flux"][i] = -0.01
    page.show_light_curve(lc)  # raised ValueError
    texts = [t.get_text() for ax in page.plot.figure.axes for t in ax.texts]
    assert any("2 frame(s)" in t and "frame_007.fits, frame_031.fits" in t for t in texts), texts


def test_photometry_page_names_the_frames_the_measurement_left_out(qtbot):
    """Frames where the target, a comparison star or the whole field was not found are named, with why, in the
    result and in red in the frame list (the owner's NY Vir night: they were measured on empty sky, silently)."""
    from PySide6.QtGui import QColor

    from astrowb.ui.workspaces import PhotometryPage

    page = PhotometryPage()
    qtbot.addWidget(page)
    page.images = [f"/night/frame_{i:03d}.fits" for i in range(62)]
    lc = synthetic_lc()
    lc["lost"] = {"frame_060.fits": ["comparison", 2], "frame_061.fits": ["aligned"]}
    page.show_light_curve(lc)
    text = page.result.text()
    assert "2 frame(s) left out" in text and "frame_060.fits: comparison star C2" in text
    assert "frame_061.fits: the stars were not found" in text
    row = page.frame_table.item(60, 0)
    assert row.foreground().color() == QColor("#e5484d") and "C2" in row.toolTip()
    assert page.frame_table.item(5, 0).foreground().color() != QColor("#e5484d")


def test_comparison_stars_are_ticked_on_and_off_and_the_light_curve_follows(qtbot):
    """As in AstroImageJ: a comparison star is left out of the ensemble by unticking it, the light curve and the
    scatters change at once, without measuring again; the noisiest is shown in red; Ctrl+Z brings it back."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor

    from astrowb.ui.workspaces import PhotometryPage

    n = 60
    lc = synthetic_lc(n)
    comps = np.asarray(lc["comp_flux"])
    variable = 2e4 * (1 + 0.05 * np.sin(np.arange(n) / 3))  # C3 varies by 5 %
    comps = np.column_stack([comps, variable])
    lc["comp_flux"], lc["comp_flux_err"] = comps.tolist(), np.sqrt(comps).tolist()
    page = PhotometryPage()
    qtbot.addWidget(page)
    page.target, page.comps, page.extras = (10.0, 10.0), [(20.0, 20.0), (30.0, 30.0), (40.0, 40.0)], []
    page.show_light_curve(lc)
    rows = {page.star_table.item(i, 0).text(): i for i in range(page.star_table.rowCount())}
    scat = {k: float(page.star_table.item(rows[k], 5).text()) for k in ("C1", "C2", "C3")}
    assert max(scat, key=scat.get) == "C3" and scat["C3"] > 2 * scat["C1"]  # C1 and C2 see C3 among the others
    assert page.star_table.item(rows["C3"], 5).foreground().color() == QColor("#e5484d")
    before = np.asarray(page.light_curve["rel_flux"])
    page.star_table.item(rows["C3"], 0).setCheckState(Qt.Unchecked)
    after = np.asarray(page.light_curve["rel_flux"])
    t = np.asarray(lc["target_flux"])
    assert np.allclose(after, t / comps[:, :2].sum(axis=1)) and not np.allclose(before, after)
    assert "left out: C3" in page.result.text()
    page.undo_stack.undo()
    assert page.comp_off == set() and np.allclose(page.light_curve["rel_flux"], before)
    for k in ("C1", "C2"):  # the last one cannot be left out
        page.star_table.item(rows[k], 0).setCheckState(Qt.Unchecked)
    page.star_table.item(rows["C3"], 0).setCheckState(Qt.Unchecked)
    assert len(page.comp_off) == 2


def test_photometry_steps_open_one_after_the_other(qtbot, tmp_path):
    """The controls are in four numbered steps: the one being worked on opens, the earlier ones fold with a tick
    (the images step stays open: its frame list shows the frames left out), and every one opens with a click."""
    from astrowb.ui.workspaces import PhotometryPage

    for i in range(3):
        h = fits.Header({"DATE-OBS": f"2026-11-15T20:{i:02d}:00", "EXPTIME": 10.0})
        fits.PrimaryHDU(field(4.0, seed=i).astype(np.float32), h).writeto(tmp_path / f"f{i}.fits")
    page = PhotometryPage()
    qtbot.addWidget(page)
    s = page.sections
    assert s[0].button.isChecked() and not s[1].button.isChecked()
    page.set_images([str(tmp_path / f"f{i}.fits") for i in range(3)])
    assert s[1].button.isChecked() and s[0].button.text().startswith("✓")
    page._clicked(60.3, 70.6)
    page._clicked(140.2, 60.1)
    assert s[2].button.isChecked() and not s[1].button.isChecked() and s[1].button.text().startswith("✓")
    page.show_apertures(
        {
            "r_ap": 5.0,
            "r_in": 15.0,
            "r_out": 20.0,
            "fwhm": 4.0,
            "best_snr_radius": 5.0,
            "encircled_at_aperture": 0.9,
            "profile_r": [0.5, 1.0],
            "profile": [1.0, 0.5],
        }  # fmt: skip
    )
    assert s[3].button.isChecked() and s[2].button.text().startswith("✓")
    s[1].button.click()  # a step done opens again with a click
    assert s[1].button.isChecked()


def test_multi_plot_series_binning_and_template(qtbot, tmp_path):
    """plans/photometry.md item 8: the multi-plot draws the ticked series, binned, and its set-up goes to another
    night; leaving each comparison star out names the scatter of every variant."""
    from astrowb.ui.workspaces import PhotometryPage

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
    lc = synthetic_lc()
    lc["extra"] = [
        {"name": "K1", "role": "check", "rel_flux": [1.0] * 60, "rel_flux_err": [0.01] * 60},
        {"name": "T2", "role": "target", "rel_flux": [1.0] * 60, "rel_flux_err": [0.01] * 60},
    ]
    page.show_light_curve(lc)
    page.show_what.setCurrentIndex(page.show_what.findData("multi"))
    assert not page.multi_box.isHidden()
    ticked = [r["key"] for r in page._multi_rows()]
    assert ticked == ["rel_flux_T1", "rel_flux_T4", "airmass"]  # T1, the check star (T4 in AIJ's numbering), airmass
    ax = page.plot.figure.axes[0]
    assert len(ax.get_legend().get_texts()) == 3 and page._plotted is not None
    page.bin_n.setValue(6)
    assert page._plotted is None  # binned points are not frames: no clicking away
    lines = [ln for ln in page.plot.figure.axes[0].get_lines() if ln.get_label() == "airmass"]
    assert len(lines[0].get_xdata()) == 10
    page.norm_from.setText("0.30")
    page.norm_to.setText("0.35")
    saved = page.save_plot_template(tmp_path / "a.plot.json")
    page.bin_n.setValue(0)
    page.multi_series.item(0).setCheckState(Qt.Unchecked)
    page.show_what.setCurrentIndex(0)
    doc = page.open_plot_template(saved)
    assert doc["bin_n"] == 6 and page.show_what.currentData() == "multi" and page.bin_n.value() == 6
    assert [r["key"] for r in page._multi_rows()] == ticked and float(page.norm_from.text()) == pytest.approx(0.30)
    rows = page.leave_each_comparison_out()
    assert {r[0] for r in rows} == {None, 0, 1} and "without C1" in page.result.text()
    bad = tmp_path / "bad.json"
    bad.write_text("{}")
    assert page.open_plot_template(bad) is None and page.result.text().startswith("not a multi-plot")


def _trend_night(seed=2, flip=True):
    rng = np.random.default_rng(seed)
    t = 2461000.3 + np.arange(240) / 1440 * 1.5  # 6 hours, 90 s cadence
    airmass = 1.1 + 2.0 * (t - 2461000.3) ** 2 * 24  # rising through the night
    fwhm = 3 + rng.normal(0, 0.3, t.size)  # uncorrelated with the flux
    sky = 100 + rng.normal(0, 5, t.size)
    transit = 1 - 0.01 * np.clip((0.03 - np.abs(t - 2461000.42)) / 0.007, 0, 1)  # 10 min ingress and egress
    step = np.where(t >= 2461000.47, 0.006, 0.0) if flip else 0.0
    rel = transit * np.exp(-0.05 * (airmass - 1.1) + step) * (1 + rng.normal(0, 0.002, t.size))
    return t, rel, np.full(t.size, 0.002) * rel, {"airmass": airmass, "fwhm": fwhm, "sky": sky}


def test_bic_picks_the_true_model_with_the_flip():
    """plans/photometry.md item 9: an airmass trend and a jump at the meridian flip: the true model has the lowest
    BIC (out of the transit) and AstroImageJ's rule keeps it; FWHM and sky add nothing."""
    t, rel, err, cov = _trend_night()
    rows = d.detrend_bic(rel, err, cov, exclude=(2461000.385, 2461000.455), time=t, flip_time=2461000.47)
    assert len(rows) == 16  # 2^3 covariate sets, with and without the flip
    chosen = next(r for r in rows if r["chosen"])
    assert chosen["names"] == ["airmass"] and chosen["flip"]
    assert rows[0]["names"] == ["airmass"] and rows[0]["flip"]
    assert chosen["reduced_chi2"] == pytest.approx(1.0, abs=0.3)
    out = d.detrend(rel, {"airmass": cov["airmass"]}, (2461000.385, 2461000.455), t, flip_time=2461000.47)
    assert out["coefficients"]["flip"] == pytest.approx(0.006, abs=0.001)
    assert out["coefficients"]["airmass"] == pytest.approx(-0.05, abs=0.005)
    t, rel, err, cov = _trend_night(flip=False)  # no jump: the flip is not kept
    rows = d.detrend_bic(rel, err, cov, exclude=(2461000.385, 2461000.455), time=t, flip_time=2461000.47)
    assert not next(r for r in rows if r["chosen"])["flip"]


def test_spline_follows_a_slow_trend_and_bridges_the_transit():
    t, rel, _, _ = _trend_night(flip=False)
    out = d.spline_detrend(rel, t, exclude=(2461000.385, 2461000.455))
    f = np.asarray(out["rel_flux"])
    outside = np.abs(t - 2461000.42) > 0.035
    assert out["spacing_h"] >= 1.0 and out["scatter_after"] < 0.0025 < out["scatter_before"]
    depth = 1 - np.median(f[np.abs(t - 2461000.42) < 0.025]) / np.median(f[outside])
    assert depth == pytest.approx(0.01, abs=0.002)  # the transit survives the bridge


def test_photometry_page_chooses_the_detrending_by_bic(qtbot, tmp_path):
    """plans/photometry.md item 9 on the page: the flip found from PIERSIDE, the BIC table, the chosen set ticked
    and applied, the spline as a further stage, and outliers left out against their neighbours (undoable)."""
    from astrowb.ui.workspaces import PhotometryPage

    t, rel, err, cov = _trend_night()
    files = []
    for i, ti in enumerate(t):
        p = tmp_path / f"f{i:03d}.fits"
        fits.PrimaryHDU(
            np.zeros((2, 2), np.float32), fits.Header({"PIERSIDE": "EAST" if ti < 2461000.47 else "WEST"})
        ).writeto(p)
        files.append(str(p))
    comps = np.column_stack([np.full(t.size, 5e4), np.full(t.size, 3e4)])
    target = rel * comps.sum(axis=1)
    target[100] *= 1.1  # one outlier (out of the transit)
    lc = synthetic_lc(t.size) | {"file": files, "time": t.tolist(), "jd_utc": t.tolist(),
                                 "airmass": cov["airmass"].tolist(),
                                 "target_flux": target.tolist(), "target_flux_err": (0.002 * target).tolist(),
                                 "comp_flux": comps.tolist(), "comp_flux_err": np.zeros_like(comps).tolist(),
                                 "fwhm": cov["fwhm"].tolist(), "extra_flux": np.ones((t.size, 2)).tolist(),
                                 "extra_flux_err": np.ones((t.size, 2)).tolist(), "sky": [[100.0] * 5] * t.size,
                                 "peak": np.full((t.size, 5), 1000.0).tolist()}  # fmt: skip
    page = PhotometryPage()
    qtbot.addWidget(page)
    page.show_light_curve(lc)
    page.exclude_from.setText("0.385")  # the plot's time, as the axis shows it
    page.exclude_to.setText("0.455")
    out = page.leave_out_outliers()
    assert len(out) == 1 and len(page.excluded) == 1
    rows = page.choose_detrending()
    assert page.flip_time.text().startswith("0.47") or float(page.flip_time.text()) == pytest.approx(
        2461000.47, abs=0.002
    )
    chosen = next(r for r in rows if r["chosen"])
    assert chosen["names"] == ["airmass"] and chosen["flip"]
    assert page.trend_boxes["airmass"].isChecked() and not page.trend_boxes["fwhm"].isChecked()
    assert "BIC" in page.result.text() and "flip" in page.light_curve["detrend"]["coefficients"]
    page.spline_trend.setChecked(True)
    page._detrend()
    assert "spline_h" in page.light_curve["detrend"] and "spline" in page.result.text()
    page.undo_stack.undo()
    assert "spline_h" not in page.light_curve["detrend"]


def test_best_comparison_set_leaves_out_the_variable_star():
    """plans/photometry.md item 9a: one variable comparison star among six: the search leaves out exactly that
    star, exhaustively and by toggling one star at a time; the target is never used."""
    rng = np.random.default_rng(9)
    n = 200
    air = 1 + 0.2 * np.linspace(0, 1, n)  # common extinction
    comps = np.column_stack(
        [f * np.exp(-0.2 * air) * (1 + rng.normal(0, 0.003, n)) for f in (5e4, 4e4, 6e4, 3e4, 5e4, 4.5e4)]
    )
    comps[:, 3] *= 1 + 0.03 * np.sin(np.arange(n) / 3)  # C4 varies
    rows = d.best_comparison_sets(comps)
    assert rows[0][0] == (0, 1, 2, 4, 5)
    greedy = d.best_comparison_sets(comps, exhaustive_up_to=3)
    assert greedy[0][0] == (0, 1, 2, 4, 5)
    check = 2e4 * np.exp(-0.2 * air) * (1 + rng.normal(0, 0.003, n))
    assert d.best_comparison_sets(comps, check)[0][0] == (0, 1, 2, 4, 5)


def test_photometry_page_finds_the_best_comparison_set(qtbot):
    from astrowb.ui.workspaces import PhotometryPage

    rng = np.random.default_rng(4)
    n = 80
    lc = synthetic_lc(n)
    comps = np.column_stack([np.full(n, f) * (1 + rng.normal(0, 0.002, n)) for f in (5e4, 3e4, 4e4, 4.5e4)])
    comps[:, 2] *= 1 + 0.04 * np.sin(np.arange(n) / 2)  # C3 varies
    lc |= {"comp_flux": comps.tolist(), "comp_flux_err": np.sqrt(comps).tolist(), "extra_flux": None}
    page = PhotometryPage()
    qtbot.addWidget(page)
    page.target, page.comps = (10.0, 10.0), [(20.0, 20.0), (30.0, 30.0), (40.0, 40.0), (50.0, 50.0)]
    page.show_light_curve(lc)
    rows = page.find_best_comparison_set()
    assert rows[0][0] == (0, 1, 3) and page.comp_off == {2}
    assert "left out: C3" in page.result.text() and page.best_sets.count() >= 2
    page.best_sets.setCurrentIndex(1)
    page._use_best_set(1)
    assert page.comp_off == set(range(4)) - set(rows[1][0])
    page.undo_stack.undo()
    page.undo_stack.undo()
    assert page.comp_off == set()


def test_ensemble_keeps_frames_without_a_comparison_star():
    """plans/photometry.md item 13: one comparison star missing on half the frames: the ensemble of the others is
    scaled by their usual share, so the target's curve does not jump."""
    rng = np.random.default_rng(13)
    n = 100
    comps = np.column_stack([np.full(n, f) * (1 + rng.normal(0, 0.001, n)) for f in (5e4, 2e4, 3e4)])
    target = np.full(n, 4e4) * (1 + rng.normal(0, 0.001, n))
    comps[50:, 1] = np.nan  # C2 leaves the field
    rel, err = d.ensemble(target, np.sqrt(target), comps, np.sqrt(np.nan_to_num(comps)))
    assert np.isfinite(rel).all() and np.isfinite(err).all()
    assert abs(np.median(rel[50:]) / np.median(rel[:50]) - 1) < 0.001  # no jump
    assert np.median(err[50:]) > np.median(err[:50])  # fewer stars: a larger error


def test_light_curve_keeps_the_frames_a_comparison_star_left(tmp_path):
    yy, xx = np.mgrid[:120, :140]
    rng = np.random.default_rng(2)
    paths = []
    for i in range(10):
        img = rng.normal(200, 4, yy.shape)
        stars = [(40.0, 40.0, 5e4), (100.0, 40.0, 6e4), (40.0, 90.0, 4e4), (100.0, 90.0, 5e4)]
        for k, (x, y, f) in enumerate(stars):
            if k == 2 and i >= 5:
                continue  # C2 is gone from frame 5 on
            img += f / (2 * np.pi * 2.0**2) * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * 2.0**2))
        h = fits.Header({"DATE-OBS": f"2026-11-15T20:{i:02d}:00", "EXPTIME": 10.0})
        fits.PrimaryHDU(img.astype(np.float32), h).writeto(tmp_path / f"m{i}.fits")
        paths.append(tmp_path / f"m{i}.fits")
    comps = [(100.0, 40.0), (40.0, 90.0), (100.0, 90.0)]
    lc = light_curve(paths, (40.0, 40.0), comps, 5, 12, 18, coord="13h38m17s +04d48m27s")
    assert len(lc["time"]) == 10 and not lc["lost"]
    hjd, jd = np.asarray(lc["hjd_utc"]), np.asarray(lc["jd_utc"])  # item 14: HJD with the target's position
    assert np.all(np.abs(hjd - jd) * 86400 > 60)
    mid = light_curve(paths[:2], (40.0, 40.0), comps, 5, 12, 18, header_time="mid", shutter_delay=0.5)
    assert np.allclose((np.asarray(mid["jd_utc"]) - jd[:2]) * 86400, -4.5, atol=1e-3)  # 5 s earlier, 0.5 s later
    assert lc["partial"] == {f"m{i}.fits": [2] for i in range(5, 10)}
    rel = np.asarray(lc["rel_flux"])
    assert abs(np.median(rel[5:]) / np.median(rel[:5]) - 1) < 0.005


def test_photometry_page_marks_frames_kept_without_a_comparison_star(qtbot):
    from astrowb.ui.workspaces import PhotometryPage

    lc = synthetic_lc(20)
    comps = np.asarray(lc["comp_flux"])
    comps[10:, 1] = np.nan
    lc |= {"comp_flux": comps.tolist(), "file": [f"f{i}.fits" for i in range(20)],
           "partial": {f"f{i}.fits": [2] for i in range(10, 20)}}  # fmt: skip
    page = PhotometryPage()
    qtbot.addWidget(page)
    page.images = [f"/x/f{i}.fits" for i in range(20)]
    page.show_light_curve(lc)
    assert np.isfinite(page.light_curve["rel_flux"]).all()
    assert "10 frame(s) without some comparison stars" in page.result.text()
    item = page.frame_table.item(15, 0)
    assert item.foreground().color().name() == "#f76b15" and "C2" in item.toolTip()


def test_header_time_convention_shutter_delay_and_hjd(tmp_path):
    """plans/photometry.md item 14: DATE-OBS read as start, middle or end; a shutter delay added; HJD (UTC) from
    astropy's light travel time to the Sun, within 1 s."""
    from astropy import units as u
    from astropy.coordinates import EarthLocation, SkyCoord
    from astropy.time import Time

    from astrowb import timing

    h = fits.Header({"DATE-OBS": "2026-11-15T20:00:00", "EXPTIME": 60.0})
    t0 = Time("2026-11-15T20:00:00", scale="utc")
    sec = lambda t: round((t - t0).to_value("s"), 3)  # noqa: E731
    assert sec(timing.mid_time(h)) == 30.0 and sec(timing.mid_time(h, "start")) == 30.0
    assert sec(timing.mid_time(h, "mid")) == 0.0 and sec(timing.mid_time(h, "end")) == -30.0
    assert sec(timing.mid_time(h, "start", 0.25)) == 30.25 and sec(timing.mid_time(h, "auto", 0.25)) == 30.25
    star = SkyCoord("13h38m17s +04d48m27s")
    site = EarthLocation.from_geodetic(30.33 * u.deg, 36.82 * u.deg, 2500 * u.m)
    t = Time(t0, location=site)
    ltt = t.light_travel_time(star, kind="heliocentric", ephemeris="builtin")
    want = (t.utc + ltt).jd
    assert abs(timing.hjd(t0, star, site).jd - want) * 86400 < 1
    assert abs(ltt.to_value("s")) > 60  # a real correction, not zero


def test_transit_fitted_together_with_an_airmass_trend():
    """plans/photometry.md item 16: a synthetic transit on an airmass trend: fitted together, depth and mid-time come
    back within 1 sigma; the trapezoid with only a slope in time is pulled off."""
    from astrowb.timeseries.minima import trapezoid_fit

    rng = np.random.default_rng(16)
    t = 2461000.30 + np.arange(300) / 1440.0
    air = 1.05 + 30 * (t - 2461000.30) ** 2  # curved: not a straight line in time
    t0, depth = 2461000.405, 0.015
    shape = np.clip((0.045 - np.abs(t - t0)) / 0.008, 0, 1)
    flux = (1 - depth * shape) * np.exp(-0.08 * (air - air.mean())) * (1 + rng.normal(0, 0.002, t.size))
    err = np.full(t.size, 0.002)
    fit = trapezoid_fit(t, flux, err, {"airmass": air})
    assert abs(fit["t0"] - t0) < fit["t0_err"] * 1.5 and fit["t0_err"] < 0.001
    assert abs(fit["depth"] - depth) < fit["depth_err"] * 1.5
    assert fit["coefficients"]["airmass"] == pytest.approx(-0.08, abs=0.01)
    plain = trapezoid_fit(t, flux, err)
    assert plain["bic"] > fit["bic"] + 10  # the trend in the model is worth its parameter


def test_minimum_step_fits_the_detrending_with_the_transit():
    from astrowb.photometry.steps import minimum_step

    rng = np.random.default_rng(17)
    t = 2461000.30 + np.arange(200) / 1440.0
    air = 1.05 + 30 * (t - 2461000.30) ** 2
    shape = np.clip((0.04 - np.abs(t - 2461000.37)) / 0.008, 0, 1)
    rel = (1 - 0.02 * shape) * np.exp(-0.1 * (air - air.mean())) * (1 + rng.normal(0, 0.002, t.size))
    lc = {"time": t.tolist(), "rel_flux": rel.tolist(), "rel_flux_err": [0.002] * t.size, "airmass": air.tolist()}
    out = minimum_step({"light_curve": lc}, {"method": "trapezoid", "t0": None, "period": None,
                                              "detrend_with": ["airmass"]}, None)["minimum"]  # fmt: skip
    assert abs(out["time"] - 2461000.37) < 2 * out["error"] and "airmass" in out["detrended_with"]
    with pytest.raises(ValueError, match="not in this light curve: fwhm"):
        minimum_step({"light_curve": lc}, {"method": "trapezoid", "t0": None, "period": None,
                                           "detrend_with": ["fwhm"]}, None)  # fmt: skip


def test_photometry_page_sends_the_trend_to_fit_with_the_transit(qtbot):
    from astrowb.ui.workspaces import PhotometryPage

    page = PhotometryPage()
    qtbot.addWidget(page)
    page.target, page.comps = (10.0, 10.0), [(20.0, 20.0), (30.0, 30.0)]
    page.show_light_curve(synthetic_lc())
    page.trend_boxes["airmass"].setChecked(True)
    page._detrend()  # the shown curve is detrended; the fit must get the curve before it
    page.trapezoid.setChecked(True)
    page.fit_trend.setChecked(True)
    with qtbot.waitSignal(page.minimum_requested) as sig:
        page._minimum()
    lc, params = sig.args
    assert params["detrend_with"] == ["airmass"] and lc["rel_flux"] == list(page._rel_before_detrend[0])
    page.show_minimum({"time": 2461000.4, "error": 0.0004, "time_scale": "BJD_TDB", "method": "trapezoid",
                       "depth": 0.3, "duration": 0.08, "bic": 123.4, "detrended_with": {"airmass": -0.05}})  # fmt: skip
    assert "Fitted together with the trend: airmass -0.0500" in page.result.text()


def test_photometry_page_chooses_another_measured_aperture(qtbot):
    """plans/photometry.md item 10 on the page: the radii measured at once are listed; another one is used without
    measuring again, with the aperture correction shown; Ctrl+Z goes back to the measured radius."""
    from astrowb.ui.workspaces import PhotometryPage

    n = 60
    lc = synthetic_lc(n)
    base = np.column_stack([np.asarray(lc["target_flux"]), np.asarray(lc["comp_flux"]), np.asarray(lc["extra_flux"])])
    share = np.array([0.6, 0.85, 1.0])  # light within 3, 5 and 8 px
    lc |= {"radii": [[5.0, 12.0, 18.0]] * n,
           "by_aperture": {"radii": [3.0, 5.0, 8.0], "flux": (base[:, None, :] * share[None, :, None]).tolist(),
                           "err": (np.sqrt(base)[:, None, :] * np.ones((1, 3, 1))).tolist()}}  # fmt: skip
    page = PhotometryPage()
    qtbot.addWidget(page)
    page.target, page.comps = (10.0, 10.0), [(20.0, 20.0), (30.0, 30.0)]
    page.show_light_curve(lc)
    assert not page.aperture_box.isHidden() and page.aperture_choice.currentIndex() == 1
    page.aperture_choice.activated.emit(0)
    assert page.lc_raw["target_flux"][0] == pytest.approx(0.6 * lc["target_flux"][0])
    assert "aperture correction +0.555 mag" in page.result.text()
    page.undo_stack.undo()
    assert page.lc_raw["target_flux"][0] == pytest.approx(lc["target_flux"][0])


def test_two_filter_night_gives_the_injected_colour_change(tmp_path):
    """plans/photometry.md item 11: a B / V night alternating filters, the target reddening by 0.05 mag in B − V over
    the night: one run gives both curves and the colour curve with that change; with T_bv and the comparison stars'
    colour, the standard colour."""
    from astrowb.photometry.steps import multifilter_step

    yy, xx = np.mgrid[:120, :140]
    rng = np.random.default_rng(11)
    paths = []
    for i in range(16):
        band = "B" if i % 2 == 0 else "V"
        frac = i / 15
        img = rng.normal(200, 3, yy.shape)
        target = 4e4 * (10 ** (-0.4 * 0.05 * frac) if band == "B" else 1.0)  # B fades by 0.05 mag
        for x, y, f in ((40.0, 40.0, target), (100.0, 40.0, 6e4), (40.0, 90.0, 5e4), (100.0, 90.0, 5.5e4)):
            img += f / (2 * np.pi * 2.0**2) * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * 2.0**2))
        h = fits.Header({"DATE-OBS": f"2026-11-15T20:{2 * i:02d}:00", "EXPTIME": 10.0, "FILTER": band})
        fits.PrimaryHDU(img.astype(np.float32), h).writeto(tmp_path / f"c{i:02d}.fits")
        paths.append(str(tmp_path / f"c{i:02d}.fits"))
    params = {"r_ap": 5.0, "r_in": 12.0, "r_out": 18.0, "t_ab": 1.1, "comp_colour": 0.6}
    from astrowb.engine.steps import REGISTRY

    params = REGISTRY["photometry.multifilter"].defaults | params
    out = multifilter_step({"images": paths, "target_xy": (40.0, 40.0),
                            "comps_xy": [(100.0, 40.0), (40.0, 90.0), (100.0, 90.0)]}, params, _Ctx())  # fmt: skip
    assert set(out["curves"]) == {"B", "V"} and len(out["curves"]["B"]["time"]) == 8
    c = np.asarray(out["colour"]["colour"])
    assert out["colour"]["filters"] == ["B", "V"] and out["colour"]["pairs"] == 8
    assert c[-1] - c[0] == pytest.approx(0.05 * 14 / 15, abs=0.01)  # the injected reddening (first to last pair)
    std = np.asarray(out["colour"]["standard"])
    assert np.allclose(std - 0.6, 1.1 * c)


class _Ctx:
    def progress(self, *a):
        pass

    def check(self):
        pass


def test_photometry_page_shows_the_colour_index(qtbot):
    from astrowb.ui.workspaces import PhotometryPage

    page = PhotometryPage()
    qtbot.addWidget(page)
    page.target, page.comps = (10.0, 10.0), [(20.0, 20.0), (30.0, 30.0)]
    lc = synthetic_lc()
    page.show_light_curve(lc)
    t = lc["time"][::2]
    colour = {"time": t, "colour": list(np.linspace(0, 0.05, len(t))), "colour_err": [0.003] * len(t),
              "standard": None, "filters": ["B", "V"], "pairs": len(t)}  # fmt: skip
    page.show_colour(colour, {"B": lc, "V": lc})
    assert page.show_what.currentData() == "colour" and "Δ(B − V) from +0.000 to +0.050" in page.result.text()
    assert page.plot.figure.axes[0].get_ylabel() == "Δ(B − V) (mag)"
    page.show_light_curve(lc)  # a new measurement in one filter: no colour any more
    assert page.show_what.findData("colour") == -1


def test_two_nights_with_a_star_missing_one_night_join_without_a_step(tmp_path):
    """plans/photometry.md item 12: night 2 lacks comparison star C2 all night (a 0.05 mag step in the plain relative
    flux); joined on night 1's shares there is no step; the export read back joins the same way."""
    from astrowb.photometry.nights import join_nights, read_export
    from astrowb.ui.photometry_page import export_csv

    rng = np.random.default_rng(12)

    def night(t0, drop=None):
        n = 50
        t = t0 + np.arange(n) / 1440
        comps = np.column_stack([np.full(n, f) * (1 + rng.normal(0, 0.001, n)) for f in (5e4, 4.73e3, 4.5e4)])
        target = np.full(n, 3e4) * (1 + rng.normal(0, 0.001, n))
        if drop is not None:
            comps[:, drop] = np.nan
        ce = np.sqrt(np.nan_to_num(comps))
        rel, err = d.ensemble(target, np.sqrt(target), comps, ce)
        return {"time": t.tolist(), "target_flux": target.tolist(), "target_flux_err": np.sqrt(target).tolist(),
                "comp_flux": comps.tolist(), "comp_flux_err": ce.tolist(), "rel_flux": rel.tolist(),
                "rel_flux_err": err.tolist(), "time_scale": "BJD_TDB", "file": ["f"] * n}  # fmt: skip

    a, b = night(2461000.3), night(2461001.3, drop=1)
    plain = 2.5 * np.log10(np.median(b["rel_flux"]) / np.median(a["rel_flux"]))
    assert plain == pytest.approx(0.05, abs=0.005)  # the step a plain join would show
    j = join_nights([a, b])
    rel, night_ = np.asarray(j["rel_flux"]), np.asarray(j["night"])
    assert abs(2.5 * np.log10(np.median(rel[night_ == 1]) / np.median(rel[night_ == 0]))) < 0.002
    assert j["night_offsets"][1] == pytest.approx(0.05, abs=0.005) and len(rel) == 100
    pa, pb = export_csv(a, tmp_path / "a.csv"), export_csv(b, tmp_path / "b.csv")
    j2 = join_nights([read_export(pa), read_export(pb)])
    assert np.allclose(j2["rel_flux"], j["rel_flux"], rtol=1e-6)
    with pytest.raises(ValueError, match="two nights"):
        join_nights([a])


def test_photometry_page_adds_other_nights(qtbot, tmp_path):
    from astrowb.ui.photometry_page import export_csv
    from astrowb.ui.workspaces import PhotometryPage

    page = PhotometryPage()
    qtbot.addWidget(page)
    page.target, page.comps = (10.0, 10.0), [(20.0, 20.0), (30.0, 30.0)]
    first = synthetic_lc()
    page.show_light_curve(first)
    other = synthetic_lc() | {"time": (np.asarray(first["time"]) + 1).tolist()}
    joined = page.add_nights([export_csv(other, tmp_path / "n2.csv")])
    assert len(joined["time"]) == 2 * len(first["time"]) and len(page.light_curve["time"]) == 120
    assert "2 nights joined" in page.result.text()
    bad = tmp_path / "bad.csv"
    bad.write_text("a,b\n1,2\n")
    assert page.add_nights([str(bad)]) is None and page.result.text().startswith("not a light curve exported")


def test_etd_text_and_the_csv_the_models_page_reads(tmp_path):
    """plans/photometry.md item 15: the ETD / VarAstro file is "first column the Julian date, second the brightness"
    (their FAQ), with the error third; the CSV export opens on the Models page as it is."""
    from astrowb.models.data import read_light_curve
    from astrowb.photometry.export import etd_text
    from astrowb.ui.photometry_page import export_csv

    lc = synthetic_lc()
    text, scale, unit = etd_text(lc)
    rows = [line.split() for line in text.strip().splitlines()]
    assert len(rows) == 60 and all(len(r) == 3 for r in rows) and scale == "BJD_TDB" and unit == "delta mag"
    jd = np.array([float(r[0]) for r in rows])
    assert np.allclose(jd, lc["time"], atol=1e-6) and jd[0] > 2.4e6  # the full Julian date
    dm, _ = d.delta_mag(lc["rel_flux"], lc["rel_flux_err"])
    assert float(rows[0][1]) == pytest.approx(dm[0], abs=1e-5)
    t, flux, err, _ = read_light_curve(export_csv(lc, tmp_path / "lc.csv"))
    rel = np.asarray(lc["rel_flux"])
    assert np.allclose(t, lc["time"]) and np.allclose(flux, rel / np.median(rel)) and err is not None


def test_photometry_page_exports_for_etd(qtbot, tmp_path):
    from astrowb.ui.workspaces import PhotometryPage

    page = PhotometryPage()
    qtbot.addWidget(page)
    page.target, page.comps = (10.0, 10.0), [(20.0, 20.0), (30.0, 30.0)]
    page.show_light_curve(synthetic_lc())
    out = page.export_etd(tmp_path / "e.txt")
    assert len(open(out).read().splitlines()) == 60
    assert "time standard BJD_TDB and the unit delta mag" in page.result.text()
