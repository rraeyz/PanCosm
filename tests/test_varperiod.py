import numpy as np
from astropy.table import Table
from PySide6.QtCore import Qt

from astrowb.photometry import varperiod
from astrowb.photometry.varindex import search


def make(frames=200, stars=60, period=0.37):
    rng = np.random.default_rng(3)
    t = 2460000 + np.sort(rng.uniform(0, 3, frames))
    mag = 14 + rng.normal(0, 0.01, (frames, stars)) + rng.normal(0, 0.02, frames)[:, None]
    mag[:, 7] += 0.15 * np.sin(2 * np.pi * (t - t[0]) / period)
    err = np.full_like(mag, 0.01)
    found = search(mag, err)
    corrected = mag - found["zp"][:, None]
    return t, corrected, found


def test_period_recovered_and_exports_read_back(tmp_path):
    t, corrected, found = make()
    stars = np.flatnonzero(found["candidate"])
    assert stars.tolist() == [7]
    p = varperiod.periods(t, corrected, stars)
    assert abs(p["period"][0] - 0.37) / 0.37 < 0.01
    assert 0.5 < p["power"][0] <= 1
    n = corrected.shape[1]
    result = {
        "field": {"time": t.tolist(), "xy": np.arange(2 * n, dtype=float).reshape(n, 2).tolist()},
        "variability": {
            "corrected": corrected.tolist(),
            "mean": found["mean"].tolist(),
            "flags": found["count"].tolist(),
            "indices": {k: np.asarray(v, float).tolist() for k, v in found["indices"].items()},
        },
        "candidate_periods": p,
    }
    varperiod.write_candidates(tmp_path / "c.csv", result)
    row = Table.read(tmp_path / "c.csv", format="ascii.csv")[0]
    assert row["star"] == 7 and abs(row["period_d"] - p["period"][0]) < 1e-6 and row["x"] == 14.0
    (path,) = varperiod.write_light_curves(tmp_path, result)
    lc = Table.read(path, format="ascii.ecsv")
    assert len(lc) == 200 and np.allclose(lc["mag"], corrected[:, 7], atol=1e-6)


def test_window_buttons_save_both_and_a_bad_folder_says_so(qtbot, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    from astrowb.ui import varfind_export
    from astrowb.ui.varfind_page import VarFindPage

    t, corrected, found = make()
    n = corrected.shape[1]
    result = {
        "field": {"time": t.tolist(), "xy": np.arange(2 * n, dtype=float).reshape(n, 2).tolist()},
        "variability": {
            "corrected": corrected.tolist(),
            "mean": found["mean"].tolist(),
            "flags": found["count"].tolist(),
            "indices": {k: np.asarray(v, float).tolist() for k, v in found["indices"].items()},
        },
        "candidate_periods": varperiod.periods(t, corrected, np.flatnonzero(found["candidate"])),
    }
    page = VarFindPage()
    qtbot.addWidget(page)
    varfind_export.attach(page)
    assert not page.export_table.isEnabled()
    page.result = result  # what show_result stores; its table needs the full step output
    page.export_table.setEnabled(True)  # what the wrapped show_result does
    from PySide6.QtWidgets import QFileDialog

    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a: (str(tmp_path / "c.csv"), ""))
    page.export_table.click()
    assert Table.read(tmp_path / "c.csv", format="ascii.csv")["star"][0] == 7
    assert "c.csv" in page.status.text()
    assert len(varfind_export.save_curves(page, str(tmp_path))) == 1
    shown = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a: shown.append(a))
    assert varfind_export.save_table(page, str(tmp_path / "gone" / "c.csv")) is None and shown
    periods = result["candidate_periods"]
    page.result = {**result, "candidate_periods": {**periods, "period": list(periods["period"]) + [1.0]}}
    assert varfind_export.save_table(page, str(tmp_path / "d.csv")) is None  # astropy's ValueError: in the status
    assert not (tmp_path / "d.csv").exists() and "Saved" not in page.status.text()


def _field():
    """A synthetic identified field: a 1″/px TAN WCS at (150, 20), a VSX, a GCVS and two Gaia stars."""
    from astropy.wcs import WCS

    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crpix, w.wcs.crval, w.wcs.cdelt = [51, 51], [150.0, 20.0], [-1 / 3600, 1 / 3600]
    near = w.pixel_to_world_values(12.0, 30.0)  # 2″ from star 0 at (10, 30)
    far = w.pixel_to_world_values(80.0, 80.0)  # 20″ from star 1 at (60, 70)
    vsx = [{"name": "V0001 Tst", "ra": float(near[0]), "dec": float(near[1]), "type": "EW", "period": 0.37},
           {"name": "V0002 Tst", "ra": float(far[0]), "dec": float(far[1])}]  # fmt: skip
    return {
        "header": w.to_header().tostring(),
        "variables": vsx,
        "gcvs": [{"name": "AB Tst", "ra": float(near[0]), "dec": float(near[1])}],
        "stars": {"ra": [float(near[0]), float(far[0])], "dec": [float(near[1]), float(far[1])], "variable": [1, 1]},
    }


def test_known_variables_matched_within_the_radius_and_empty_beyond():
    k = varperiod.known_variables(_field(), [[10, 30], [60, 70]], [4, 9])
    assert k["star"] == [4, 9] and k["vsx"] == ["V0001 Tst", ""] and k["vsx_type"] == ["EW", ""]
    assert k["vsx_period_d"][0] == 0.37 and np.isnan(k["vsx_period_d"][1])
    assert k["gcvs"] == ["AB Tst", ""] and k["gaia_variable"] == ["VARIABLE", ""]
    wide = varperiod.known_variables(_field(), [[60, 70]], [9], radius_arcsec=30)
    assert wide["vsx"] == ["V0002 Tst"] and wide["vsx_type"] == [""] and np.isnan(wide["vsx_period_d"][0])
    empty = varperiod.known_variables({"header": _field()["header"]}, [[10, 30]], [4])
    assert empty["vsx"] == [""] and empty["gaia_variable"] == [""]


def test_vsx_type_and_period_kept_from_the_catalogue_rows():
    from astrowb.overlays import query_catalogue

    rows = Table({"Name": ["V1"], "_RAJ2000": [1.0], "_DEJ2000": [2.0], "max": [12.0], "Type": ["RRAB"],
                  "Period": [0.55]})  # fmt: skip
    (star,) = query_catalogue(1, 2, 0.1, "vsx", query=lambda *a: rows)
    assert star["type"] == "RRAB" and star["period"] == 0.55


def test_look_up_button_names_the_candidates_and_a_failure_keeps_empty_columns(qtbot, tmp_path, monkeypatch):
    from astrowb.ui import varfind_export
    from astrowb.ui.varfind_page import VarFindPage

    t, corrected, found = make()
    n = corrected.shape[1]
    xy = np.full((n, 2), 50.0)
    xy[7] = [10, 30]
    result = {
        "field": {"time": t.tolist(), "xy": xy.tolist()},
        "variability": {
            "corrected": corrected.tolist(),
            "mean": found["mean"].tolist(),
            "rms": np.nanstd(corrected, axis=0).tolist(),
            "index": found["count"].tolist(),
            "typical": np.full(n, 0.01).tolist(),
            "candidate": found["candidate"].tolist(),
            "flags": found["count"].tolist(),
            "indices": {k: np.asarray(v, float).tolist() for k, v in found["indices"].items()},
        },
        "candidate_periods": varperiod.periods(t, corrected, np.flatnonzero(found["candidate"])),
    }
    page = VarFindPage()
    qtbot.addWidget(page)
    varfind_export.attach(page)
    page.images = ["a.fits"]
    asked = []
    page.known_requested.connect(asked.append)
    monkeypatch.setattr(varfind_export.timing, "chronological", lambda paths: list(paths))
    page.show_result(result)
    assert page.look_up.isEnabled()
    page.known_failed("network unreachable")  # what on_fail gives: the table keeps its empty columns
    assert "network" in page.status.text()
    varfind_export.save_table(page, str(tmp_path / "e.csv"))
    assert Table.read(tmp_path / "e.csv", format="ascii.csv")["vsx"].mask.all()
    page.look_up.click()
    assert asked == ["a.fits"]
    page.show_known({"field": _field()})  # what photometry.identify_field answers
    assert "1 of 1" in page.status.text()
    model = page.table.view.model()
    cols = [model.headerData(c, Qt.Horizontal) for c in range(model.columnCount())]
    assert model.data(model.index(0, cols.index("VSX"))) == "V0001 Tst"
    varfind_export.save_table(page, str(tmp_path / "k.csv"))
    row = Table.read(tmp_path / "k.csv", format="ascii.csv")[0]
    assert row["vsx"] == "V0001 Tst" and row["vsx_type"] == "EW" and row["vsx_period_d"] == 0.37
    assert row["gcvs"] == "AB Tst" and row["gaia_variable"] == "VARIABLE"
