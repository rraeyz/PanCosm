"""CAL-7: a night with lights only finds its masters in the library with the reason; an old flat is offered marked;
a moved dust mote shows in the comparison."""

import numpy as np
from astropy.io import fits

from astrowb.calibration.library import Library, compare

SHAPE = (100, 140)


def master(tmp_path, name, kind, date, **cards):
    h = fits.Header({"IMAGETYP": kind, "DATE-OBS": date, "XBINNING": 2, "YBINNING": 2} | cards)
    p = tmp_path / "in" / name
    p.parent.mkdir(exist_ok=True)
    fits.PrimaryHDU(np.ones(SHAPE, np.float32), h).writeto(p, overwrite=True)
    return p


def light(date, **cards):
    return fits.Header({"IMAGETYP": "LIGHT", "DATE-OBS": date, "NAXIS": 2, "NAXIS1": SHAPE[1], "NAXIS2": SHAPE[0],
                        "XBINNING": 2, "YBINNING": 2} | cards)  # fmt: skip


def test_a_night_with_lights_only(tmp_path):
    lib = Library(tmp_path / "lib")
    lib.add(master(tmp_path, "master_bias_00.fits", "Bias", "2026-10-01T18:00:00"))
    lib.add(master(tmp_path, "master_dark_01.fits", "Dark", "2026-11-01T18:00:00", EXPTIME=60.0, **{"CCD-TEMP": -10.0}))
    lib.add(master(tmp_path, "master_dark_02.fits", "Dark", "2026-11-02T18:00:00", EXPTIME=300.0))
    lib.add(master(tmp_path, "master_flat_03.fits", "Flat", "2026-11-01T17:00:00", FILTER="V"))
    lib.add(master(tmp_path, "master_flat_03.fits", "Flat", "2026-11-12T17:00:00", FILTER="R"))  # same name, kept apart
    night = light("2026-11-13T21:00:00", EXPTIME=60.0, FILTER="V", **{"CCD-TEMP": -9.5})
    bias = lib.best("bias", night)
    assert bias and bias["valid"] and "43 days old" in bias["why"]
    dark = lib.best("dark", night)
    assert dark and dark["path"].endswith("master_dark_01.fits")  # the 60 s one, not the 300 s
    flat = lib.best("flat", night)
    assert flat and not flat["valid"] and "older than its 7 days" in flat["why"]  # offered marked, not silently
    assert lib.best("flat", light("2026-11-13T21:00:00", FILTER="B")) is None  # no B flat at all
    assert Library(tmp_path / "lib").best("bias", night)["path"] == bias["path"]  # the index survives
    lib.retire(bias["path"])
    assert lib.best("bias", night) is None


def test_a_moved_dust_mote_shows():
    yy, xx = np.indices((200, 260))

    def flat(x, y):
        return 30000 * (1 - 0.04 * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * 6.0**2)))

    same = compare(flat(100, 120), flat(100, 120))
    moved = compare(flat(100, 120), flat(160, 80))
    assert same["moved_dust"] == [] and abs(same["ratio_median"] - 1) < 1e-9
    assert len(moved["moved_dust"]) == 2 and moved["ratio_rms"] > 0.002
