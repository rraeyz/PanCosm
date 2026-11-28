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
    from astrowb.photometry.lcfile import read

    saved = read(tmp_path / "light_curve.lc.ecsv")  # the file beside the frames, as File → Export writes it
    assert np.allclose(saved["rel_flux"], direct["rel_flux"], rtol=1e-12)
    # three frames only, given on the command line
    out = tmp_path / "three.lc.ecsv"
    assert cli.main(["recipe", str(path), "--json", "--quiet", "--set", f"images={json.dumps(paths[:3])}",
                     "--set", f"output={out}"]) == 0  # fmt: skip
    assert len(json.loads(capsys.readouterr().out)["light_curve"]["rel_flux"]) == 3
    assert len(read(out)["rel_flux"]) == 3


def test_recipe_finds_the_stars_by_the_sky_on_another_night(tmp_path, capsys):
    """PHO-20: a recipe made on one night runs on another whose frames sit 15 px and −9 px off: the stars come from
    their RA, Dec on the new night's solved first frame; on the night it was made, its pixels are used as they are."""
    from astropy.wcs import WCS

    def wcs(dx, dy):
        w = WCS(naxis=2)
        w.wcs.ctype, w.wcs.crval, w.wcs.crpix = ["RA---TAN", "DEC--TAN"], [30.0, 40.0], [60.0 + dx, 50.0 + dy]
        w.wcs.cdelt = [-1 / 3600, 1 / 3600]
        return w.to_header()

    nights = {}
    for name, (dx, dy) in (("a", (0, 0)), ("b", (15, -9))):
        nights[name] = []
        for i in range(3):
            img = np.roll(field(4.0, seed=60 + i), (dy, dx), axis=(0, 1)).astype(np.float32)
            h = wcs(dx, dy)
            h.update({"DATE-OBS": f"2026-11-1{5 if name == 'a' else 6}T20:0{i}:00", "EXPTIME": 30.0})
            fits.PrimaryHDU(img, h).writeto(tmp_path / f"{name}{i}.fits")
            nights[name].append(str(tmp_path / f"{name}{i}.fits"))
    xy = [s[:2] for s in STARS]
    w = WCS(fits.getheader(nights["a"][0]))
    sky = {"target": [float(v) for v in w.pixel_to_world_values(*xy[0])],
           "comps": [[float(v) for v in w.pixel_to_world_values(*c)] for c in xy[1:3]], "extra": []}  # fmt: skip
    params = {"r_ap": 6.0, "r_in": 15.0, "r_out": 20.0}
    recipe = light_curve_recipe(nights["a"], xy[0], xy[1:3], params, ref_image=nights["a"][0], stars_sky=sky)
    path = save(recipe, tmp_path / "night.json")
    moved = [(x + 15, y - 9) for x, y in xy]
    direct = light_curve(nights["b"], moved[0], moved[1:3], 6.0, 15.0, 20.0)
    assert cli.main(["recipe", str(path), "--json", "--quiet", "--set", f"images={json.dumps(nights['b'])}"]) == 0
    got = json.loads(capsys.readouterr().out)["light_curve"]
    assert np.allclose(got["rel_flux"], direct["rel_flux"], rtol=1e-6)
    same = light_curve(nights["a"], xy[0], xy[1:3], 6.0, 15.0, 20.0)
    assert cli.main(["recipe", str(path), "--json", "--quiet"]) == 0
    assert np.allclose(json.loads(capsys.readouterr().out)["light_curve"]["rel_flux"], same["rel_flux"], rtol=1e-12)


def test_the_guides_recipe_command_runs(tmp_path, monkeypatch, capsys):
    """PHO-20: the command of guide 06 (Exporting), word for word, runs a recipe on another night's two frames."""
    import shlex
    from pathlib import Path

    from astrowb.photometry.lcfile import read

    guide = Path(cli.__file__).parent / "resources/guide/en/06-photometry.md"
    line = next(s for s in guide.read_text(encoding="utf-8").splitlines() if s.startswith("astrowb-cli recipe"))
    monkeypatch.chdir(tmp_path)
    (tmp_path / "n2").mkdir()
    for i, name in enumerate(["n1.fits", "n2/f001.fits", "n2/f002.fits"]):
        h = fits.Header({"DATE-OBS": f"2026-11-15T20:{i:02d}:00", "EXPTIME": 30.0})
        fits.PrimaryHDU(field(4.0, seed=40 + i).astype(np.float32), h).writeto(name)
    xy = [s[:2] for s in STARS]
    save(light_curve_recipe(["n1.fits"], xy[0], xy[1:3], {"r_ap": 6.0, "r_in": 15.0, "r_out": 20.0}), "night.json")
    assert cli.main(shlex.split(line)[1:] + ["--json", "--quiet"]) == 0
    assert len(json.loads(capsys.readouterr().out)["light_curve"]["rel_flux"]) == 2
    assert len(read(tmp_path / "n2.lc.ecsv")["rel_flux"]) == 2
