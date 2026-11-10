"""CAL-2 item 3: a user rule changes how a frame is classified, filter names that mean the same filter are joined,
and "why" says what decided."""

import numpy as np
from astropy.io import fits

from astrowb.calibration.frames import why
from astrowb.engine.steps import execute


class Ctx:
    def progress(self, *a):
        pass

    def check(self):
        pass


def test_a_rule_and_filter_aliases(tmp_path):
    for i, (obstype, filt) in enumerate((("SKY", "Clear"), ("SKY", "Lum"), ("OBJECT", "L"))):
        h = fits.Header({"OBSTYPE": obstype, "FILTER": filt, "EXPTIME": 10.0})
        fits.PrimaryHDU(np.ones((8, 8), np.float32), h).writeto(tmp_path / f"f{i}.fits")
    plain = execute("calibration.scan", {"folder": str(tmp_path)}, {}, Ctx())["frames"]
    assert [f["kind"] for f in plain] == ["unknown", "unknown", "light"]  # SKY means nothing to the conventions
    rules = [{"key": "OBSTYPE", "value": "sky", "kind": "flat"}]
    ruled = execute("calibration.scan", {"folder": str(tmp_path)},
                    {"rules": rules, "filter_aliases": {"clear": "L", "Lum": "L"}}, Ctx())["frames"]  # fmt: skip
    assert [f["kind"] for f in ruled] == ["flat", "flat", "light"]
    assert {f["filter"] for f in ruled} == {"L"}
    h = fits.getheader(tmp_path / "f0.fits")
    assert why(h, "f0.fits", rules) == "your rule: OBSTYPE = sky is a flat"
    assert why(fits.Header({"IMAGETYP": "Dark Frame"}), "x.fits") == "IMAGETYP = 'Dark Frame' is a dark"
    assert why(fits.Header({"EXPTIME": 0.0}), "x.fits") == "no exposure time: a bias"
