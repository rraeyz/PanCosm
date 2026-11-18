import numpy as np
from astropy.io import fits
from astropy.table import Table

from astrowb.core import reproduce


def _fits(path, data, stamp):
    h = fits.PrimaryHDU(np.asarray(data, dtype=float))
    h.header["DATE"] = stamp
    h.writeto(path)
    return str(path)


def test_files_snapshot_and_compare(tmp_path):
    a = _fits(tmp_path / "a.fits", np.ones((3, 3)), "2026-01-01")
    b = _fits(tmp_path / "b.fits", np.ones((3, 3)), "2026-02-02")  # only the header time differs
    c = np.ones((3, 3))
    c[1, 1] = 3.5
    d = _fits(tmp_path / "d.fits", c, "x")
    assert reproduce.compare(a, b) == "identical"
    assert reproduce.compare(a, d) == 2.5
    assert reproduce.compare(a, _fits(tmp_path / "e.fits", np.ones((2, 2)), "x")) == "different shape"
    out = {"image": a, "frames": [b, "not a file"], "n": 1}
    assert reproduce.files_in(out) == [("image", tmp_path / "a.fits"), ("frames[0]", tmp_path / "b.fits")]
    before = reproduce.snapshot(out, tmp_path / "run")
    assert before["image"].parent == tmp_path / "run" / "original" and (tmp_path / "a.fits").exists()


def test_ecsv_bytes_and_report(tmp_path):
    for name, v in (("o.ecsv", [1.0, 2.0]), ("n.ecsv", [1.0, 2.25])):
        Table({"x": v}).write(tmp_path / name)
    assert reproduce.compare(tmp_path / "o.ecsv", tmp_path / "n.ecsv") == 0.25
    (tmp_path / "1.txt").write_text("a")
    (tmp_path / "2.txt").write_text("b")
    assert reproduce.compare(tmp_path / "1.txt", tmp_path / "2.txt") == "differs"
    old = {"t": str(tmp_path / "o.ecsv"), "gone": str(tmp_path / "1.txt"), "k": 2.0, "same": 1}
    before = reproduce.snapshot(old, tmp_path / "r")
    (tmp_path / "1.txt").unlink()
    new = {"t": str(tmp_path / "n.ecsv"), "k": 2.5, "same": 1, "extra": str(tmp_path / "2.txt")}
    lines = reproduce.report(before, new, old)
    assert "t: 0.25" in lines and "gone: missing in the new run" in lines and "extra: only in the new run" in lines
    assert "k: 0.5" in lines and "same: identical" in lines
