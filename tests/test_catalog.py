"""Catalogue magnitudes and the standard-system calibration, on simulated stars with known magnitudes."""

import numpy as np
import pytest
from astropy.io import fits

from astrowb.engine.steps import execute
from astrowb.photometry import catalog


def test_gaia_to_johnson_cousins():
    # a solar-type star, BP-RP = 0.82: V is ~0.15 mag fainter than G (Riello et al. 2021)
    assert catalog.from_gaia("V", 10.0, 0.82) == pytest.approx(10.152, abs=0.002)
    assert catalog.from_gaia("I", 10.0, 0.82) < 10.0 - 0.5  # red light: I brighter than G


def test_star_magnitude_prefers_apass_then_gaia():
    apass = {"Bmag": 12.6, "e_Bmag": 0.02, "Vmag": 12.0, "e_Vmag": 0.03, "g'mag": None, "r'mag": None, "i'mag": None}
    gaia = {"Gmag": 11.85, "e_Gmag": 0.003, "BPmag": 12.2, "RPmag": 11.38}
    v = catalog.star_magnitude({"apass": apass, "gaia": gaia}, "V")
    assert v["mag"] == 12.0 and v["source"] == "APASS DR9" and v["colour"] == pytest.approx(0.6)
    r = catalog.star_magnitude({"apass": apass, "gaia": gaia}, "R")
    assert r["source"].startswith("Gaia") and 11.3 < r["mag"] < 11.8
    assert catalog.star_magnitude({"apass": None, "gaia": gaia}, "CV")["source"].startswith("Gaia")  # clear filter
    assert catalog.star_magnitude({"apass": None, "gaia": None}, "V") is None


def test_calibrate_recovers_magnitudes_and_colour_term():
    rng = np.random.default_rng(2)
    n, k_true = 60, 0.08
    cat = np.array([11.0, 11.6, 12.1, 12.5]), np.array([0.2, 0.6, 1.0, 1.4])
    target_mag, target_col = 12.3 + 0.2 * np.sin(np.linspace(0, 6, n)), 0.8
    zp = 20.0 + 0.3 * np.linspace(0, 1, n)  # airmass and clouds change the zero point through the night

    def flux(m, col):
        return 10 ** (-0.4 * (m - zp - k_true * col)) * (1 + rng.normal(0, 0.002, n))

    comp_flux = np.column_stack([flux(m, c) for m, c in zip(*cat, strict=True)])
    t_flux = flux(target_mag, target_col)
    rel = t_flux / comp_flux.sum(axis=1)
    lc = {"comp_flux": comp_flux.tolist(), "target_flux": t_flux.tolist(), "rel_flux": rel.tolist()}
    lc["rel_flux_err"] = (0.003 * rel).tolist()
    comps = [{"mag": m, "colour": c} for m, c in zip(*cat, strict=True)]
    out = catalog.calibrate(lc, comps, target_colour=target_col)
    assert out["colour_term"] == pytest.approx(k_true, abs=0.01)
    assert np.allclose(out["mag"], target_mag, atol=0.01) and out["suspect"] == []
    comps[2] = {"mag": 12.1 - 0.3, "colour": 1.0}  # a catalogue value that is wrong (or a variable star)
    out = catalog.calibrate(lc, comps, target_colour=target_col)
    assert out["suspect"] == [2] and np.allclose(out["mag"], target_mag, atol=0.01)  # left out, result unharmed


class Ctx:
    def progress(self, *a):
        pass

    def check(self):
        pass


def test_catalog_step_uses_the_wcs(tmp_path, monkeypatch):
    h = fits.Header(
        {
            "CTYPE1": "RA---TAN",
            "CTYPE2": "DEC--TAN",
            "CRVAL1": 31.0,
            "CRVAL2": 46.7,
            "CRPIX1": 50.5,
            "CRPIX2": 40.5,
            "CD1_1": -0.0005,
            "CD1_2": 0.0,
            "CD2_1": 0.0,
            "CD2_2": 0.0005,
        }
    )
    fits.PrimaryHDU(np.zeros((80, 100), np.float32), h).writeto(tmp_path / "a.fits")
    asked = []

    def fake_fetch(coord, radius_arcsec=3.0):
        asked.append(coord)
        return {"apass": {"Bmag": 11.5, "Vmag": 11.0, "e_Vmag": 0.02}, "gaia": None}

    monkeypatch.setattr(catalog, "vizier_fetch", fake_fetch)
    inputs = {"image": str(tmp_path / "a.fits"), "target_xy": [49.5, 39.5], "comps_xy": [[10.0, 10.0]]}
    out = execute("photometry.catalog", inputs, {"filter": "V"}, Ctx())["catalog"]
    assert out["comps"][0]["mag"] == 11.0 and len(asked) == 2
    assert asked[0].ra.deg == pytest.approx(31.0, abs=1e-6) and asked[0].dec.deg == pytest.approx(46.7, abs=1e-6)
    fits.PrimaryHDU(np.zeros((80, 100), np.float32)).writeto(tmp_path / "b.fits")
    with pytest.raises(ValueError, match="plate-solve"):
        execute("photometry.catalog", inputs | {"image": str(tmp_path / "b.fits")}, {}, Ctx())


def test_photometry_page_shows_standard_magnitudes(qtbot, tmp_path):
    from astrowb.ui.workspaces import PhotometryPage, export_csv

    page = PhotometryPage()
    qtbot.addWidget(page)
    n = 20
    comp = np.full((n, 2), [1000.0, 500.0])
    target = np.linspace(400, 600, n)
    page.light_curve = {
        "time": np.linspace(2461000.3, 2461000.5, n).tolist(),
        "time_scale": "BJD_TDB",
        "file": ["f"] * n,
        "comp_flux": comp.tolist(),
        "target_flux": target.tolist(),
        "rel_flux": (target / 1500).tolist(),
        "rel_flux_err": [0.001] * n,
    }
    page.show_catalog(
        {
            "filter": "V",
            "target": None,
            "comps": [
                {"mag": 11.0, "err": 0.02, "colour": None, "source": "APASS DR9"},
                {"mag": 11.0 + 2.5 * np.log10(2), "err": 0.02, "colour": None, "source": "Gaia DR3 → JC"},
            ],
        }
    )
    assert "Comparison 2:" in page.result.text() and "Target V:" in page.result.text()
    assert page.light_curve["mag"][0] == pytest.approx(11.0 + 2.5 * np.log10(1000 / 400), abs=1e-6)
    export_csv(page.light_curve | {"jd_utc": page.light_curve["time"]}, tmp_path / "lc.csv")
    assert "V_mag" in (tmp_path / "lc.csv").read_text().splitlines()[0]
