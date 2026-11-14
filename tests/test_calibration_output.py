"""CAL-14: the size a run will write is estimated within 10 %, and a disk too small refuses before writing."""

import numpy as np
import pytest
from astropy.io import fits

from astrowb.calibration import output
from astrowb.engine.steps import execute


class Ctx:
    def progress(self, *a):
        pass

    def check(self):
        pass


def test_the_estimate_matches_what_is_written(tmp_path):
    rng = np.random.default_rng(0)
    raw = tmp_path / "raw"
    raw.mkdir()
    for i in range(5):
        fits.PrimaryHDU((300 + rng.normal(0, 3, (300, 400))).astype(np.float32),
                        fits.Header({"IMAGETYP": "BIAS"})).writeto(raw / f"b{i}.fits")  # fmt: skip
    for i in range(12):
        fits.PrimaryHDU((800 + rng.normal(0, 10, (300, 400))).astype(np.float32),
                        fits.Header({"IMAGETYP": "LIGHT", "EXPTIME": 5.0})).writeto(raw / f"l{i}.fits")  # fmt: skip
    scan = execute("calibration.scan", {"folder": str(raw)}, {}, Ctx())
    out = execute("calibration.run", {"frames": scan["frames"], "output_dir": str(tmp_path / "cal")}, {}, Ctx())
    written = sum(p.stat().st_size for p in (tmp_path / "cal").rglob("*.fits"))
    assert out["estimated_bytes"] == pytest.approx(written, rel=0.1)


def test_a_full_disk_refuses(tmp_path):
    with pytest.raises(ValueError, match="GB free"):
        output.check_space(tmp_path / "not" / "yet", 10**18)
    assert output.check_space(tmp_path, 1000) > 1000
