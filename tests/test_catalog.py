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


def test_gaia_from_the_esa_archive_when_no_vizier_server_answers(monkeypatch):
    import astropy.units as u
    from astropy.coordinates import SkyCoord
    from astropy.table import Table

    from astrowb import gaia, mirrors
    from astrowb.photometry import coefficients

    def down(service, query, patience=15.0):
        raise ConnectionError("tunnel closed")

    asked = []

    def esa(ra, dec, radius_deg, row_limit=5000):
        asked.append(radius_deg)
        return Table(
            {
                "_RAJ2000": [10.0, 10.01],
                "_DEJ2000": [20.0, 20.0],
                "Gmag": [12.0, 13.0],
                "e_Gmag": [0.001, 0.002],
                "BPmag": [12.4, 13.5],
                "RPmag": [11.5, 12.4],
            }
        )

    monkeypatch.setattr(mirrors, "cds", down)
    monkeypatch.setattr(gaia, "photometry", esa)
    entry = catalog.vizier_fetch(SkyCoord(10.0101 * u.deg, 20.0 * u.deg))
    assert entry["apass"] is None and entry["gaia"]["Gmag"] == 13.0  # the nearer star, not the brighter
    assert catalog.star_magnitude(entry, "V")["source"] == "Gaia DR3 → JC"
    sky = SkyCoord([10.0, 10.01, 10.3] * u.deg, [20.0, 20.0, 20.0] * u.deg)
    mags = coefficients.catalogue_magnitudes(sky, ("B", "V"))
    assert np.isnan(mags["B"]).all() and np.isfinite(mags["V"][:2]).all() and np.isnan(mags["V"][2])
    monkeypatch.setattr(gaia, "photometry", lambda *a, **k: Table({"_RAJ2000": [], "_DEJ2000": []}))
    with pytest.raises(ConnectionError):  # nothing anywhere and VizieR down: the error, not an empty answer
        coefficients.catalogue_magnitudes(sky, ("B", "V"))


def test_no_colour_term_from_scatter_over_a_narrow_colour_range():
    # four red comparison stars (B-V 0.53-0.86) whose catalogue magnitudes scatter by 0.05: their slope is noise,
    # and extrapolated to a blue target (B-V 0.12) it moved the target by 0.27 mag on a real LCO night
    colours = np.array([0.86, 0.53, 0.82, 0.80])
    offsets = np.array([-0.035, -0.002, 0.067, -0.030])
    mags = np.array([11.769, 11.392, 11.592, 11.989])
    flux = 10 ** (-0.4 * (mags - offsets - 23.6))
    lc = {
        "comp_flux": [flux.tolist()] * 3,
        "target_flux": [1e5] * 3,
        "rel_flux": [1.0] * 3,
        "rel_flux_err": [0.001] * 3,
    }
    comps = [{"mag": m, "colour": c} for m, c in zip(mags, colours, strict=True)]
    out = catalog.calibrate(lc, comps, target_colour=0.12)
    assert out["colour_term"] == 0.0
    # a real colour term over the same colours, measured by the stars, is kept
    flux = 10 ** (-0.4 * (mags - 0.3 * colours - 23.6))
    out = catalog.calibrate(lc | {"comp_flux": [flux.tolist()] * 3}, comps, target_colour=0.12)
    assert out["colour_term"] == pytest.approx(0.3, abs=0.01)
