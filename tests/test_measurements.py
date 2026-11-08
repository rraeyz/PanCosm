"""plans/photometry.md item 6: the measurements table with AstroImageJ's column names."""

import numpy as np
import pytest

from astrowb.photometry.measurements import filter_rows, measurements, star_names


def lc(n=4):
    rng = np.random.default_rng(0)
    t = 1000.0 + rng.uniform(0, 100, n)
    c = rng.uniform(800, 900, (n, 2))
    return {
        "file": [f"f{i}.fits" for i in range(n)],
        "time": (2460000.5 + np.arange(n) * 0.01).tolist(),
        "time_scale": "BJD_TDB",
        "jd_utc": (2460000.49 + np.arange(n) * 0.01).tolist(),
        "target_flux": t.tolist(),
        "target_flux_err": (np.sqrt(t)).tolist(),
        "comp_flux": c.tolist(),
        "comp_flux_err": np.sqrt(c).tolist(),
        "rel_flux": (t / c.sum(1)).tolist(),
        "rel_flux_err": (0.01 * t / c.sum(1)).tolist(),
        "xy": [[[10.0, 20.0], [30.0, 40.0], [50.0, 60.0]]] * n,
        "sky": [[5.0, 6.0, 7.0]] * n,
        "peak": [[100.0, 70000.0, 90.0]] * n,
        "saturation": 65000.0,
        "radii": [[4.0, 10.0, 16.0]] * n,
        "airmass": [1.1] * n,
        "fwhm": [3.0] * n,
    }


def test_names_and_columns_as_astroimagej():
    assert star_names(2, 1) == ["T1", "C2", "C3", "T4"]
    cols, flags = measurements(lc())
    for name in (
        "Label",
        "slice",
        "J.D.-2400000",
        "JD_UTC",
        "BJD_TDB",
        "AIRMASS",
        "FWHM_Mean",
        "rel_flux_T1",
        "rel_flux_err_T1",
        "rel_flux_SNR_T1",
        "tot_C_cnts",
        "tot_C_err",
    ):
        assert name in cols
    for star in ("T1", "C2", "C3"):
        for col in (
            "X(FITS)",
            "Y(FITS)",
            "Source-Sky",
            "Source_Error",
            "Source_SNR",
            "Sky/Pixel",
            "N_Src_Pixels",
            "Peak",
            "Source_Radius",
            "Sky_Rad(min)",
            "Sky_Rad(max)",
        ):
            assert f"{col}_{star}" in cols
    assert cols["X(FITS)_T1"][0] == 11.0  # 0-based 10 is FITS pixel 11
    assert cols["N_Src_Pixels_T1"][0] == pytest.approx(np.pi * 16)
    assert cols["tot_C_cnts"][0] == pytest.approx(sum(lc()["comp_flux"][0]))
    assert set(flags) == {(r, "Peak_C2") for r in range(4)}  # the saturated comparison star, on every frame


def test_filter_like_astroimagej():
    cols, _ = measurements(lc())
    rows = filter_rows(cols, "Source-Sky_T1 > 1050 and AIRMASS < 2")
    assert rows == [i for i, f in enumerate(cols["Source-Sky_T1"]) if f > 1050]
    with pytest.raises(ValueError):
        filter_rows(cols, "nonsense > 1")
    with pytest.raises(ValueError):
        filter_rows(cols, "rel_flux_T1 >>> 1")
