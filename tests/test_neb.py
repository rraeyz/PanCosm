"""PHO-23: a faint neighbour's deep eclipse is a potential NEB; quiet stars are cleared."""

import numpy as np

from astrowb.photometry import neb


def test_dispositions():
    rng = np.random.default_rng(0)
    n = 400
    t = np.linspace(0, 0.3, n)
    target = 50000 * (1 + rng.normal(0, 0.001, n))
    window = (t > 0.1) & (t < 0.2)
    eclipsing = 3000 * (1 - 0.2 * window) * (1 + rng.normal(0, 0.003, n))  # 3 mag fainter, a 20 % eclipse
    quiet = 3000 * (1 + rng.normal(0, 0.003, n))
    faint = 30 * (1 + rng.normal(0, 0.05, n))  # 8 mag fainter: it would need more than all its light
    empty = 0.5 * (1 + rng.normal(0, 0.1, n))
    rows = neb.check(target, {"neb": eclipsing, "quiet": quiet, "faint": faint, "empty": empty}, 5.0, pixels=10)
    got = {r["name"]: r for r in rows}
    # about 3 mag fainter (2.5 with the buffer): a 5 ppt target depth needs about 50 ppt there
    dmag = got["quiet"]["dmag"]
    assert (
        abs(dmag - 2.5 * np.log10(50000 / 3000)) < 0.01
        and abs(got["quiet"]["required_ppt"] - 5 * 10 ** ((dmag - 0.5) / 2.5)) < 1e-9
    )
    assert got["quiet"]["disposition"] == "Cleared"
    assert got["neb"]["disposition"] in ("Not cleared", "Likely cleared")  # the eclipse inflates its scatter
    assert got["faint"]["disposition"] == "Cleared - too faint"
    assert got["empty"]["disposition"] == "Not cleared - flux too low"
    assert neb.best(["Not cleared", "Likely cleared", "Cleared - too faint"]) == "Likely cleared"
    idx = neb.candidates([1.0, 4.0, 9.0, 2.0], 5.0, 150, [30, 60, 90, 200])
    assert list(idx) == [0, 1]


def test_a_night_checked_star_by_star(tmp_path):
    """The step on frames: a neighbour that dims by 30 % mid-night is not cleared, a quiet one is cleared, a star
    too far away or too faint is not checked at all."""
    from astropy.io import fits

    from astrowb.engine.steps import execute

    rng = np.random.default_rng(1)
    yy, xx = np.mgrid[:120, :160]

    def star(x, y, f):
        return f * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * 1.5**2)) / (2 * np.pi * 1.5**2)

    stars = [(40, 60, 4e5), (100, 60, 4e5), (60, 30, 3e4), (60, 90, 3e4), (150, 110, 3e4)]  # T, C, NEB, quiet, far
    paths = []
    for i in range(30):
        dim = 0.7 if 12 <= i < 18 else 1.0
        img = 200 + sum(star(x, y, f * (dim if k == 2 else 1)) for k, (x, y, f) in enumerate(stars))
        h = fits.Header({"DATE-OBS": f"2026-01-01T00:{i:02d}:00", "EXPTIME": 30.0})
        p = tmp_path / f"f{i:02d}.fits"
        fits.PrimaryHDU(rng.poisson(img).astype(np.float32), h).writeto(p)
        paths.append(str(p))
    gmag = [10.0, 10.0, 12.8, 12.8, 12.8]
    field = {"scale": 2.0, "stars": {"x": [s[0] for s in stars], "y": [s[1] for s in stars], "gmag": gmag}}

    class Ctx:
        def progress(self, *a):
            pass

        def check(self):
            pass

    inputs = {"images": paths, "target_xy": [40, 60], "comps_xy": [[100, 60]], "field": field}
    params = {"depth_ppt": 5.0, "radius_arcsec": 100.0, "r_ap": 5.0, "r_in": 8.0, "r_out": 12.0}
    rows = execute("photometry.neb_check", inputs, params, Ctx())["neb"]
    got = {(round(r["x"]), round(r["y"])): r for r in rows}
    assert set(got) == {(60, 30), (60, 90)}  # the comparison (0 mag) cannot make the depth
    assert got[(60, 90)]["disposition"] == "Cleared" and got[(60, 30)]["disposition"] != "Cleared"
