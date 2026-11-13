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


def test_save_all_writes_the_whole_night(tmp_path):
    """PHO-27 item 5: one folder with the light curve, the measurements table, the star list, the fit and the plot."""
    import csv
    import json

    from matplotlib.figure import Figure

    from astrowb.photometry.reports.save_all import save_all

    lc = measured() | {"target_flux": [5e4] * 12, "target_flux_err": [200.0] * 12}
    fig = Figure()
    fig.add_subplot().plot(lc["time"], lc["rel_flux"])
    fit = {"values": {"tc": 2459800.51}, "errors": {"tc": np.float64(3e-4)},
           "derived": {"depth_ppt": 20.0, "t14_h": 2.1}, "beta": 1.1, "chi2r": 1.1, "model": [1]}  # fmt: skip
    stars = {"target": (100, 100), "comps": [(50, 60), (150, 40), (30, 170)], "radii": (4, 10, 16)}
    files = save_all(tmp_path / "night", lc, stars, fit, fig)
    aavso = save_all(tmp_path / "aavso", lc, aavso={"OBSCODE": "XYZ", "STAR_NAME": "Qatar-1", "FILTER": "R"})
    from astrowb.photometry.reports import aavso_exoplanet

    text = (tmp_path / "aavso" / "AAVSO_exoplanet.txt").read_text(encoding="utf-8")
    assert "AAVSO_exoplanet.txt" in {p.name for p in aavso} and aavso_exoplanet.validate(text) == []
    assert "AAVSO_exoplanet.txt" not in {p.name for p in save_all(tmp_path / "x", lc, aavso={"STAR_NAME": "Q"})}
    names = sorted(p.name for p in files)
    assert names == ["ExoClock.txt", "ExoClock_form.txt", "light_curve.lc.ecsv", "light_curve.pdf", "light_curve.png",
                     "measurements.csv", "methods.txt", "references.bib", "stars.json", "summary.pdf",
                     "transit_fit.json"]  # fmt: skip
    assert (tmp_path / "night" / "summary.pdf").read_bytes().startswith(b"%PDF")
    text = (tmp_path / "night" / "methods.txt").read_text(encoding="utf-8")
    assert "12 frames" in text and "aperture of 4.0 px" in text and "3 comparison stars" in text
    assert "Eastman et al. (2010)" in text and "2459800.51000 ± 0.00030 BJD_TDB" in text
    assert (tmp_path / "night" / "references.bib").read_text(encoding="utf-8").count("@ARTICLE") == 3
    assert lcfile.read(tmp_path / "night" / "light_curve.lc.ecsv")["rel_flux"] == lc["rel_flux"]
    rows = list(csv.reader(open(tmp_path / "night" / "measurements.csv", encoding="utf-8")))
    assert len(rows) == 13 and "rel_flux_T1" in rows[0]
    back = json.loads((tmp_path / "night" / "transit_fit.json").read_text(encoding="utf-8"))
    assert back["errors"]["tc"] == 3e-4 and "model" not in back
