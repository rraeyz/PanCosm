import numpy as np
from astropy.table import Table

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
    varfind_export.save_table(page, str(tmp_path / "c.csv"))
    assert Table.read(tmp_path / "c.csv", format="ascii.csv")["star"][0] == 7
    assert len(varfind_export.save_curves(page, str(tmp_path))) == 1
    shown = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a: shown.append(a))
    assert varfind_export.save_table(page, str(tmp_path / "gone" / "c.csv")) is None and shown
