"""CAL-23: 48 frames with the wrong OBJECT and no coordinates get the right OBJECT, RA / Dec and BJD_TDB (equal to
timing's within 1 ms) in copies; the originals untouched."""

import numpy as np
import pytest
from astropy.coordinates import EarthLocation, SkyCoord
from astropy.io import fits

from astrowb import timing
from astrowb.calibration import headers

TARGET = {"name": "NY Vir", "ra": 204.70, "dec": -2.03}
SITE = {"lat": 36.8242, "lon": 30.3356, "height": 2500.0}


def night(tmp_path, n=48):
    paths = []
    for i in range(n):
        h = fits.Header({"OBJECT": "NSVS07826147", "DATE-OBS": f"2026-05-14T20:{i:02d}:00", "EXPTIME": 30.0})
        p = tmp_path / "raw" / f"f{i:02d}.fits"
        p.parent.mkdir(exist_ok=True)
        fits.PrimaryHDU(np.zeros((4, 4), np.float32), h).writeto(p)
        paths.append(str(p))
    return paths


def test_the_wrong_object_fixed_and_bjd_written_in_copies(tmp_path):
    paths = night(tmp_path)
    rules = {"set": {"OBJECT": "NY Vir", "OBJCTRA": "13 38 48.0", "OBJCTDEC": "-02 01 48"}, "target": TARGET,
             "site": SITE, "computed": ["DATE-AVG", "JD_UTC", "BJD_TDB", "AIRMASS"]}  # fmt: skip
    rows = headers.preview(paths[:2], rules)
    assert {"file": "f00.fits", "key": "OBJECT", "old": "NSVS07826147", "new": "NY Vir"} in rows
    out = headers.apply(paths, rules, tmp_path / "fixed")
    assert len(out) == 48 and fits.getheader(paths[0])["OBJECT"] == "NSVS07826147"  # originals untouched
    h = fits.getheader(out[10])
    assert h["OBJECT"] == "NY Vir" and h["DATE-AVG"].startswith("2026-05-14T20:10:15")
    where = EarthLocation.from_geodetic(SITE["lon"], SITE["lat"], SITE["height"])
    truth = timing.bjd_tdb(timing.mid_time(h), SkyCoord(204.70, -2.03, unit="deg"), where).jd
    assert abs(h["BJD_TDB"] - truth) * 86400 < 1e-3 and 1.0 < h["AIRMASS"] < 3.0
    assert any("keywords edited" in str(c) for c in h["HISTORY"])


def test_rename_delete_and_the_clock_and_the_guard(tmp_path):
    paths = night(tmp_path, 2)
    rules = {"rename": {"OBJECT": "OLDOBJ"}, "delete": ["EXPTIME"], "computed": ["JD_UTC"], "clock_offset_s": 2.0}
    with pytest.raises(ValueError):
        headers.apply(paths, rules)  # neither a folder nor in place: nothing written
    out = headers.apply(paths, {"computed": ["JD_UTC"], "clock_offset_s": 2.0}, tmp_path / "a")
    base = fits.getheader(out[0])["JD_UTC"]
    out = headers.apply(paths, rules, tmp_path / "b")
    h = fits.getheader(out[0])
    assert h["OLDOBJ"] == "NSVS07826147" and "OBJECT" not in h and "EXPTIME" not in h
    assert base == pytest.approx(timing.mid_time(fits.getheader(paths[0])).utc.jd + 2 / 86400, abs=1e-7)
    headers.apply(paths[:1], {"set": {"OBSERVER": "IA"}}, in_place=True)
    assert fits.getheader(paths[0])["OBSERVER"] == "IA"


def test_the_dialog_previews_and_writes_copies(tmp_path, qapp):
    from astrowb.ui.headers_dialog import HeadersDialog

    paths = night(tmp_path, 3)
    d = HeadersDialog()
    d.choose(paths)
    d.object.setText("NY Vir")
    d.ra.setText("13:38:48.1")
    d.dec.setText("-02:01:49")
    rows = d.preview()
    assert any(r["key"] == "OBJECT" and r["new"] == "NY Vir" for r in rows) and d.table.rowCount() == len(rows)
    out = d.write(out_dir=tmp_path / "copies")
    h = fits.getheader(out[0])
    assert h["OBJECT"] == "NY Vir" and h["RA"] == pytest.approx(204.70042, abs=1e-4) and "BJD_TDB" in h
    assert d.write(in_place=True, confirmed=True) and fits.getheader(paths[0])["OBJECT"] == "NY Vir"
