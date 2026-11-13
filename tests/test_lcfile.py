"""PHO-48: a light curve written and read back is the same dict; Astropy reads it with units and the aliases."""

import numpy as np
import pytest
from astropy.table import Table

from astrowb.photometry import lcfile


def measured(n=12):
    rng = np.random.default_rng(0)
    return {
        "file": [f"f{i:02d}.fits" for i in range(n)], "time": (2459800.5 + np.arange(n) / 1440).tolist(),
        "time_scale": "BJD_TDB", "rel_flux": rng.normal(1, 0.002, n).tolist(),
        "rel_flux_err": [0.002] * n, "comp_flux": rng.normal(1e5, 300, (n, 3)).tolist(),
        "xy": rng.normal(100, 1, (n, 4, 2)).tolist(), "peak": rng.normal(2e4, 10, (n, 4)).tolist(),
        "radii": [[4.0, 10.0, 16.0]] * n, "hjd_utc": None, "saturation": 65535.0, "fwhm": [3.1] * (n - 1) + [None],
        "lost": {"f99.fits": ["target"]}, "partial": {}, "fixed": [], "coord": "02:04:10 +46:41:16",
    }  # fmt: skip


def test_round_trip(tmp_path):
    lc = measured()
    p = lcfile.write(lc, tmp_path / "n.lc.ecsv", provenance={"step": "photometry.light_curve"})
    back = lcfile.read(p)
    assert back.keys() == lc.keys()
    for k, v in lc.items():
        assert back[k] == v, k
    t = Table.read(p)
    assert str(t["time"].unit) == "d" and np.allclose(t["flux"], lc["rel_flux"]) and t["xy"].shape == (12, 4, 2)
    assert t.meta["provenance"]["step"] == "photometry.light_curve"
    t.meta["version"] = 99
    t.write(tmp_path / "old.lc.ecsv", format="ascii.ecsv")
    with pytest.raises(ValueError, match="not a light-curve file"):
        lcfile.read(tmp_path / "old.lc.ecsv")
