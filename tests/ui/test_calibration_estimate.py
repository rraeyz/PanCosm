"""CAL-14: the Calibrate stage shows what the run writes and refuses when the disk is too small."""

from astrowb.calibration import output
from astrowb.ui.calibrate_page import CalibratePage


def _frames():
    f = {"kind": "light", "shape": (100, 200), "exptime": 5.0, "filter": "V", "binning": (1, 1)}
    return [dict(f, path=f"l{i}.fits") for i in range(3)] + [dict(f, kind="bias", path="b.fits")]


def _page(qtbot, tmp_path, monkeypatch, free=10**12):
    monkeypatch.setattr(output.shutil, "disk_usage", lambda p: type("U", (), {"free": free})())
    page = CalibratePage()
    qtbot.addWidget(page)
    page.frames = _frames()
    page.output.setText(str(tmp_path / "cal"))
    return page


def test_the_line_names_files_size_folder_and_space(qtbot, tmp_path, monkeypatch):
    page = _page(qtbot, tmp_path, monkeypatch)
    page.split_colour.setChecked(False)  # a colour split would make four files of each light
    text = page.estimate.text()
    assert text.startswith("This run writes about 4 files, ") and str(tmp_path / "cal") in text
    assert text.endswith("free space 1000.0 GB")


def test_a_disk_too_small_refuses(qtbot, tmp_path, monkeypatch):
    page = _page(qtbot, tmp_path, monkeypatch, free=1000)
    got = []
    page.run_requested.connect(lambda *a: got.append(a))
    page._run()
    assert not got and "GB free" in page.result.text()
