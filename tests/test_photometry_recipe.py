"""PHO-20: the window's measurement saved as a recipe runs again without the window, with the same result; an
input given on the command line replaces the recipe's own."""

import json

import numpy as np
from astropy.io import fits
from test_apertures import STARS, field

from astrowb import cli
from astrowb.engine import automation
from astrowb.photometry.lightcurve import light_curve
from astrowb.photometry.recipe import light_curve_recipe, save


def test_recipe_runs_as_the_window_did(tmp_path, capsys):
    paths = []
    for i in range(4):
        h = fits.Header({"DATE-OBS": f"2026-11-15T20:{i:02d}:00", "EXPTIME": 30.0})
        fits.PrimaryHDU(field(4.0, seed=40 + i).astype(np.float32), h).writeto(tmp_path / f"f{i}.fits")
        paths.append(str(tmp_path / f"f{i}.fits"))
    xy = [s[:2] for s in STARS]
    params = {"r_ap": 6.0, "r_in": 15.0, "r_out": 20.0, "sky_method": "centroid"}
    path = save(light_curve_recipe(paths, xy[0], xy[1:3], params), tmp_path / "night.json")
    direct = light_curve(paths, xy[0], xy[1:3], 6.0, 15.0, 20.0, sky_method="centroid")
    assert automation.needed(automation.load(path), automation.defaults(automation.load(path))) == []
    assert cli.main(["recipe", str(path), "--json", "--quiet"]) == 0
    got = json.loads(capsys.readouterr().out)["light_curve"]
    assert np.allclose(got["rel_flux"], direct["rel_flux"], rtol=1e-12)
    # three frames only, given on the command line
    assert cli.main(["recipe", str(path), "--json", "--quiet", "--set", f"images={json.dumps(paths[:3])}"]) == 0
    assert len(json.loads(capsys.readouterr().out)["light_curve"]["rel_flux"]) == 3
