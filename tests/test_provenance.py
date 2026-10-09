"""ARC-11: products carry how they were made, readable by people (HISTORY) and by the program (read)."""

import numpy as np
from astropy.io import fits
from astropy.table import Table

from astrowb.core import provenance


def test_record_round_trips_through_fits_and_ecsv(tmp_path):
    raw = tmp_path / "light 1.fits"  # a space in a name: FITS drops trailing spaces of cards
    fits.PrimaryHDU(np.zeros((8, 8), np.float32)).writeto(raw)
    rec = provenance.record("calibration.run", {"sigma": 3.0, "note": "a b  c ", "path": tmp_path}, {"light": raw})
    header = provenance.to_fits(fits.Header(), rec)
    out = tmp_path / "out.fits"
    fits.PrimaryHDU(np.zeros((8, 8), np.float32), header).writeto(out)
    assert provenance.read(out) == rec
    h = fits.getheader(out)
    assert h["PROCSTEP"] == "calibration.run" and h["PROCHASH"] == provenance.digest(rec) and h["SWVERS"]
    assert any("sigma = 3.0" in str(v) for v in h["HISTORY"])  # what a person reads in DS9
    t = Table({"x": [1, 2]})
    t.meta = provenance.to_ecsv(t.meta, rec)
    t.write(tmp_path / "t.ecsv")
    assert provenance.read(tmp_path / "t.ecsv") == rec


def test_checksum_sees_a_change_and_the_hash_ignores_the_time(tmp_path):
    f = tmp_path / "big.bin"
    data = bytearray(9 << 20)
    f.write_bytes(data)
    first = provenance.checksum(f)
    data[-10] = 1
    f.write_bytes(data)
    assert provenance.checksum(f) != first
    a = provenance.record("s", {"k": 1}, {"in": f})
    b = dict(a, made="2000-01-01T00:00:00+00:00")
    assert provenance.digest(a) == provenance.digest(b)
    assert provenance.digest(a) != provenance.digest(dict(a, params={"k": 2}))


def test_the_last_record_wins_when_a_file_went_through_two_steps():
    h = fits.Header()
    provenance.to_fits(h, {"step": "one", "params": {}, "inputs": {}, "versions": {"application": "1"}, "made": "t"})
    second = {"step": "two", "params": {"x": 1}, "inputs": {}, "versions": {"application": "1"}, "made": "t"}
    provenance.to_fits(h, second)
    assert provenance.from_header(h) == second and provenance.from_header(fits.Header()) is None
