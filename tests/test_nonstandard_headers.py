"""Files from capture programs that break the FITS rules a little (a lower-case keyword, NaN or 1.0.0 as a
number) must calibrate, stack and process: astropy refused to write their headers (seen on real data)."""

import numpy as np
import pytest
from astropy.io import fits

from astrowb.engine.steps import execute


class Ctx:
    def progress(self, *a):
        pass

    def check(self):
        pass


def raw_file(path, kind, exptime, level, filt="W1:04 R W2:00 Empty"):
    """A FITS file written byte by byte, as such programs do."""
    rng = np.random.default_rng(abs(hash(path.name)) % 2**32)
    yy, xx = np.mgrid[:40, :50]
    star = (level - 300) * 20 * np.exp(-((xx - 20) ** 2 + (yy - 18) ** 2) / 4) if kind.startswith("Light") else 0
    comp = (level - 300) * 30 * np.exp(-((xx - 36) ** 2 + (yy - 25) ** 2) / 4) if kind.startswith("Light") else 0
    data = (level + star + comp + rng.normal(0, 3, (40, 50))).astype(">f4")
    cards = [
        "SIMPLE  =                    T",
        "BITPIX  =                  -32",
        "NAXIS   =                    2",
        "NAXIS1  =                   50",
        "NAXIS2  =                   40",
        f"IMAGETYP= '{kind}'",
        f"exptime =  {exptime:19.3f}",  # lower-case keyword
        f"FILTER  = '{filt}'",
        "CCD-TEMP=   -95.54999999999998",
        "XBINNING=                    2",
        "YBINNING=                    2",
        "FOCUS   =                  NaN",  # not a FITS number
        "SWVER   =              1.0.0.0",  # not a number at all
        "DATE-OBS= '2025-01-10T20:00:00'",
        "SITELAT = '36 49 27'",
        "SITELONG= '30 20 08'",
        "SITEELEV= '2496.00 / Meters'",  # a number with its unit inside the string (seen on real data)
        "EGAIN   = '1.60 e-/ADU'",
        "END",
    ]
    header = "".join(c.ljust(80) for c in cards).ljust(2880).encode("ascii")
    raw = data.tobytes()
    path.write_bytes(header + raw + b"\0" * (-len(raw) % 2880))


def test_calibrate_stack_and_process_nonstandard_files(tmp_path):
    night = tmp_path / "night"
    for folder, kind, t, level, n in (
        ("BDF", "Bias Frame", 0.0, 300, 3),
        ("BDF", "Flat Field", 1.0, 20000, 3),
        ("Light", "Light Frame", 10.0, 1300, 3),
    ):
        (night / folder).mkdir(parents=True, exist_ok=True)
        for i in range(n):
            raw_file(night / folder / f"{kind.split()[0]}_{i}.fits", kind, t, level)
    frames = execute("calibration.scan", {"folder": str(night)}, {}, Ctx())["frames"]
    assert sorted({f["kind"] for f in frames}) == ["bias", "flat", "light"]
    out = execute("calibration.run", {"frames": frames, "output_dir": str(tmp_path / "cal")}, {}, Ctx())
    assert len(out["calibrated"]) == 3
    h = fits.getheader(out["calibrated"][0])
    assert h["EXPTIME"] == 10.0 and h["FILTER"] == "W1:04 R W2:00 Empty"
    assert np.median(fits.getdata(out["calibrated"][0])) == pytest.approx(1000, rel=0.05)
    stack = execute("stacking.stack", {"images": out["calibrated"], "output": str(tmp_path / "s.fits")}, {}, Ctx())
    assert fits.getdata(stack["stack"]).shape == (40, 50)
    flip = execute(
        "image.process", {"image": out["calibrated"][0], "operation": "flip"}, {"args": {"axis": "x"}}, Ctx()
    )
    assert fits.getheader(flip["image"])["EXPTIME"] == 10.0
    lc = execute(
        "photometry.light_curve",
        {"images": out["calibrated"], "target_xy": [20, 18], "comps_xy": [[36, 25]], "coord": "13:39:01.3 -02:07:17.6"},
        {},
        Ctx(),
    )["light_curve"]
    assert len(lc["rel_flux"]) == 3 and lc["time_scale"].startswith("BJD") and np.all(np.isfinite(lc["time"]))


def test_longitude_written_in_hours_is_recognised():
    """TUBITAK National Observatory (MaxIm DL + ACE): SITELONG '02 01 20.533' is in hours (30.33 deg E)."""
    from astrowb import timing

    h = fits.Header()
    h["DATE-OBS"] = "2018-07-10T18:35:14.05"
    h["SITELAT"] = "+36 49 17.000"
    h["SITELONG"] = "02 01 20.533"
    h["SITEELEV"] = "2496.00   / Meters"
    h["SIDEREAL"] = "15:51:05.2"
    where = timing.location(h)
    assert where.lon.deg == pytest.approx(30.3355, abs=1e-3) and where.height.value == pytest.approx(2496)
    del h["SIDEREAL"]  # without the sidereal time: degrees, as the FITS conventions say
    assert timing.location(h).lon.deg == pytest.approx(2.0224, abs=1e-3)
