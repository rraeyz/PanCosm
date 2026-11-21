"""CAL-14: a calibration write is complete or absent; the result equals a plain write."""

import numpy as np
import pytest
from astropy.io import fits

from astrowb.calibration import masters, planes_out
from astrowb.core.atomic import write_fits


def _half_write(self, name, *a, **k):  # a FITS writer that dies after some bytes
    open(name, "wb").write(b"SIMPLE  =" + b" " * 100)
    raise OSError("disk went away")


def test_an_interrupted_write_leaves_nothing(tmp_path, monkeypatch):
    path = tmp_path / "m.fits"
    with monkeypatch.context() as m:
        m.setattr(fits.HDUList, "writeto", _half_write)
        with pytest.raises(OSError):
            masters.save(path, np.ones((4, 5)), fits.Header())
    assert list(tmp_path.iterdir()) == []


def test_a_failed_overwrite_keeps_the_old_file(tmp_path, monkeypatch):
    path = tmp_path / "m.fits"
    masters.save(path, np.ones((4, 5)), fits.Header())
    before = path.read_bytes()
    monkeypatch.setattr(fits.HDUList, "writeto", _half_write)
    with pytest.raises(OSError):
        masters.save(path, np.zeros((4, 5)), fits.Header())
    assert path.read_bytes() == before and [p.name for p in tmp_path.iterdir()] == ["m.fits"]


def test_a_leftover_part_is_removed_and_the_file_equals_a_plain_write(tmp_path):
    path = tmp_path / "m.fits"
    (tmp_path / "m.fits.part").write_bytes(b"junk")
    data = np.arange(20, dtype=np.float32).reshape(4, 5)
    planes_out.save_master(path, data, fits.Header({"A": 1}), var=data + 1)
    assert [p.name for p in tmp_path.iterdir()] == ["m.fits"]
    with fits.open(path) as h:
        assert np.array_equal(h["SCI"].data, data) and np.array_equal(h["VAR"].data, data + 1)
    plain = tmp_path / "plain.fits"
    fits.HDUList([fits.PrimaryHDU(data, fits.Header({"A": 1}))]).writeto(plain)
    write_fits(fits.PrimaryHDU(data, fits.Header({"A": 1})), tmp_path / "x.fits")
    assert (tmp_path / "x.fits").read_bytes() == plain.read_bytes()
