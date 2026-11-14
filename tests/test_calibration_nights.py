"""CAL-19: three nights in one folder tree calibrate in one run, each into its own folder; a night without flats
borrows the nearest night's, and the report says so."""

import numpy as np
from astropy.io import fits

from astrowb.calibration import nights
from astrowb.engine.steps import execute


class Ctx:
    def progress(self, *a):
        pass

    def check(self):
        pass


def test_three_nights_in_one_run(tmp_path):
    rng = np.random.default_rng(2)
    shape = (60, 80)
    for night, evening, has_flats in (
        ("n1", "2026-11-10", True),
        ("n2", "2026-11-11", False),
        ("n3", "2026-11-13", True),
    ):
        folder = tmp_path / "data" / night
        folder.mkdir(parents=True)
        for i in range(3):
            fits.PrimaryHDU((300 + rng.normal(0, 3, shape)).astype(np.float32),
                            fits.Header({"IMAGETYP": "BIAS", "DATE-OBS": f"{evening}T17:0{i}:00"})).writeto(
                folder / f"b{i}.fits")  # fmt: skip
            if has_flats:
                h = fits.Header({"IMAGETYP": "FLAT", "EXPTIME": 1.0, "DATE-OBS": f"{evening}T16:3{i}:00"})
                fits.PrimaryHDU((20300 + rng.normal(0, 100, shape)).astype(np.float32), h).writeto(
                    folder / f"f{i}.fits"
                )
        for i in range(2):  # lights after midnight UTC still belong to the evening's night
            next_day = evening[:-2] + f"{int(evening[-2:]) + 1:02d}"
            h = fits.Header({"IMAGETYP": "LIGHT", "EXPTIME": 30.0, "DATE-OBS": f"{next_day}T01:0{i}:00"})
            fits.PrimaryHDU((800 + rng.normal(0, 10, shape)).astype(np.float32), h).writeto(folder / f"l{i}.fits")
    scan = execute("calibration.scan", {"folder": str(tmp_path / "data")}, {}, Ctx())
    assert set(nights.split(scan["frames"])) == {"2026-11-10", "2026-11-11", "2026-11-13"}
    report = nights.run(scan["frames"], tmp_path / "cal", ctx=Ctx())
    assert [r["night"] for r in report] == ["2026-11-10", "2026-11-11", "2026-11-13"]
    assert all(r["calibrated"] == 2 for r in report)
    second = report[1]
    assert second["borrowed"] == [{"kind": "flat", "from": "2026-11-10"}]  # the nearest night with flats
    assert (tmp_path / "cal" / "2026-11-11").is_dir() and len(list((tmp_path / "cal").iterdir())) == 3
