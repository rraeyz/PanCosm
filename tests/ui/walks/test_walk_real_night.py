"""Walk on a real night (VAL-8 with real data): the HAT-P-32 b transit of the EXOTIC sample (142 frames from a
6-inch telescope) used as a user would — frames opened, the target and two comparison stars clicked, the radii
chosen by the program, the light curve measured, the exact transit fitted, the night checked, everything saved.
Run with ASTROWB_VALIDATION_DATA=<folder containing HatP32Dec202017> (skipped otherwise)."""

import os
from pathlib import Path

import pytest

DATA = Path(os.environ.get("ASTROWB_VALIDATION_DATA", "/nonexistent")) / "HatP32Dec202017"
T0, P = 2455867.402743, 2.1500082  # the NASA Exoplanet Archive ephemeris EXOTIC uses for this night


@pytest.mark.skipif(not DATA.is_dir(), reason="validation data not available")
def test_hatp32_night_as_a_user(walk, tmp_path):
    frames = sorted(DATA.glob("*.FITS"))
    h = walk("en")
    h.area("photometry")
    phot = h.main.photometry_page
    h.answer(*frames)
    h.click("load_button")
    h.wait(lambda: phot.viewer.data is not None and len(phot.images) == 142)
    for x, y in ((424, 286), (465, 183), (512, 263)):  # the target, then the comparison stars, as EXOTIC's inits
        h.click_image(phot.viewer, x, y)
    assert len(phot.comps) == 2
    h.type("coord", "02:04:10.28 +46:41:16.2")
    h.click("apertures_button")
    h.wait(lambda: not h.busy())
    h.click("measure_button", budget=60.0)
    h.wait(lambda: phot.light_curve is not None)
    lc = phot.light_curve
    assert len(lc["time"]) == 142 and lc["time_scale"] == "BJD_TDB"  # clicks a few pixels off still find the stars
    h.type("period", str(P))
    h.click("transit_button")
    h.wait(lambda: phot.transit_result.text().startswith("Mid-transit"))
    fit = phot.transit_fit[1]
    tc = T0 + round((fit["values"]["tc"] - T0) / P) * P
    o_c = (fit["values"]["tc"] - tc) * 1440
    assert abs(o_c) < max(3 * fit["errors"]["tc"] * 1440, 5), o_c  # on the published ephemeris
    assert 15 < fit["derived"]["depth_ppt"] < 30  # Rp/Rs 0.149: 22 ppt
    assert phot.checks.verdict.text()  # the Checks tab judged the night
    from astrowb.ui.area_windows import _save_all

    saved = {p.name for p in _save_all(h.window, phot, str(tmp_path / "all"))}
    assert {"light_curve.lc.ecsv", "measurements.csv", "summary.pdf", "ExoClock.txt", "methods.txt"} <= saved
    h.check()


DATA_ROOT = Path(__file__).resolve().parents[3] / "data"
PALOMAR = DATA_ROOT / "calibration" / "palomar-lfc"
AIDRA = DATA_ROOT / "photometry" / "ai-dra-tess" / "tess-s0024-2-1_254.075800_52.698300_21x21_astrocut.fits"


@pytest.mark.skipif(
    not (PALOMAR / "ccd.037.0.fits").is_file(), reason="python tools/fetch_data.py calibration/palomar-lfc"
)
def test_palomar_raw_night_calibrated_as_a_user(walk, tmp_path):
    """A real raw night (Palomar 5 m LFC): the folder chosen, scanned, the masters made and the two lights calibrated;
    every frame sorted by its header; the calibrated lights flat (the flat removed the vignetting)."""
    import numpy as np
    from astropy.io import fits

    h = walk("en")
    h.area("calibrate")
    page = h.main.calibrate_page
    h.type("folder", str(PALOMAR))
    h.type("output", str(tmp_path / "cal"))
    h.click("scan_button")
    h.wait(lambda: page.table.rowCount() > 0 and page.run_button.isEnabled())
    assert page.table.rowCount() == 12
    h.click("run_button", budget=60.0)
    h.wait(lambda: bool(getattr(page, "calibrated", None)))
    assert len(page.calibrated) == 2
    for p in page.calibrated:
        d = fits.getdata(p).astype(float)
        ny, nx = d.shape
        centre = np.nanmedian(d[ny // 3 : 2 * ny // 3, nx // 3 : 2 * nx // 3])
        corner = np.nanmedian(d[: ny // 6, : nx // 6])
        assert abs(corner / centre - 1) < 0.05, (p, corner / centre)  # no vignetting left
    h.check()


@pytest.mark.skipif(not AIDRA.is_file(), reason="python tools/fetch_data.py photometry/ai-dra-tess")
def test_ai_dra_period_from_tess_as_a_user(walk, tmp_path):
    """AI Dra from a TESS cut-out: the light curve measured from the pixels, loaded in Light curves and period, the
    period searched; VSX gives 1.1988 d."""
    import numpy as np

    from astrowb.io.bayer import fits_paths
    from astrowb.photometry.lightcurve import light_curve

    lc = light_curve(fits_paths([AIDRA]), (10, 10), [], 2.5, 6, 9)  # the cadences, as Photometry opens the file
    t, f = np.asarray(lc["time"]), np.asarray(lc["target_flux"])
    ok = np.isfinite(t) & np.isfinite(f)
    csv = tmp_path / "ai_dra.csv"
    np.savetxt(csv, np.column_stack([t[ok], f[ok] / np.nanmedian(f[ok])]), delimiter=",", header="time,flux")
    h = walk("en")
    h.area("timeseries")
    h.answer(csv)
    h.click("period_page.load_button")
    page = h.page.period_page
    h.wait(lambda: len(page.time) > 1000)
    h.click("period_page.search_button", budget=30.0)
    h.wait(lambda: page.best is not None)
    best = float(page.best)
    assert min(abs(best - 1.19881), abs(best - 2 * 1.19881), abs(best - 1.19881 / 2)) < 0.002, best
    h.check()


EROS = sorted((DATA_ROOT / "astrometry" / "eros-lco").glob("*.fits.fz"))


@pytest.mark.skipif(len(EROS) < 3, reason="python tools/fetch_data.py astrometry/eros-lco")
def test_eros_positions_match_jpl(tmp_path):
    """433 Eros on three LCO frames (SAAO, 2026-08-08): the asteroid marked on the first and last frame, its
    positions measured on the frames' own plate solutions and compared with JPL Horizons for that site (skipped
    offline). The telescope tracked the asteroid 19″ from its pointing: it stays on one pixel, the stars move."""
    import json
    import urllib.parse
    import urllib.request

    import numpy as np
    from astropy.time import Time

    from astrowb.api import run

    out = run("astrometry.moving", images=[str(p) for p in EROS], first_xy=[1233.5, 1223.7], last_xy=[1233.9, 1224.1])
    pos = out["positions"]
    assert len(pos) == 3 and not out["unsolved"]
    q = {"format": "json", "COMMAND": "'433'", "EPHEM_TYPE": "OBSERVER", "CENTER": "'coord@399'",
         "COORD_TYPE": "'GEODETIC'", "SITE_COORD": "'20.8098883,-32.3806333,1.760'", "QUANTITIES": "'1'",
         "TLIST": "'" + "','".join(str(Time(p["time"]).jd) for p in pos) + "'", "ANG_FORMAT": "DEG"}  # fmt: skip
    try:
        with urllib.request.urlopen(
            "https://ssd.jpl.nasa.gov/api/horizons.api?" + urllib.parse.urlencode(q), timeout=60
        ) as r:
            text = json.load(r)["result"]
    except OSError:
        pytest.skip("JPL Horizons not reachable")
    rows = text.split("$$SOE")[1].split("$$EOE")[0].strip().splitlines()
    for p, row in zip(pos, rows, strict=True):
        ra, dec = (float(v) for v in row.split()[-2:])
        sep = np.hypot((p["ra"] - ra) * np.cos(np.radians(dec)), p["dec"] - dec) * 3600
        assert sep < 1.5, (p["time"], sep)  # astrometric RA / Dec within 1.5″ (pixels of 0.57″, a fast NEO)
