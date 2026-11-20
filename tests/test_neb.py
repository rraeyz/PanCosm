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
    # with the predicted window (frames 12–17 dim by 30 %): the box finds 300 ppt there, nothing on the quiet star
    from astropy.time import Time

    t0 = Time("2026-01-01T00:00:00").jd + 30 / 86400  # mid-exposure of the first frame
    params |= {"tc": t0 + 14.5 / 1440, "duration_h": 6 / 60}
    got = {(round(r["x"]), round(r["y"])): r for r in execute("photometry.neb_check", inputs, params, Ctx())["neb"]}
    neb_box, quiet = got[(60, 30)], got[(60, 90)]
    assert abs(neb_box["box_ppt"] - 300) < 5 * neb_box["box_err_ppt"] + 10 and neb_box["box_ppt"] > 250
    assert abs(quiet["box_ppt"]) < 4 * quiet["box_err_ppt"]


def test_neb_plots_and_folder(tmp_path):
    """The TFOP files with the check's rows write NEB/: a curve per neighbour, the Δmag-vs-RMS plot, the field."""
    from astrowb.photometry.reports.tfop import tfop_files

    t = 2460000 + np.arange(40) / 100
    flux = np.ones(40)
    flux[15:25] = 0.7
    rows = [{"name": f"{k}: G13.0 @ 40″", "disposition": d, "gmag": 13.0, "separation": 40.0, "dmag": 3.0,
             "required_ppt": 50.0, "rms_ppt": 5.0, "ratio": 10.0, "x": 30.0 + 20 * k, "y": 40.0, "time": t,
             "flux": flux if k == 1 else np.ones(40), "window": (t[15], t[24])}
            for k, d in ((1, "Not cleared"), (2, "Cleared"))]  # fmt: skip
    image = np.random.default_rng(0).normal(100, 5, (80, 120))
    files = {p.name for p in tfop_files(tmp_path, {"time": t}, None, {"target": (10, 40)}, rows, image)}
    assert {"star_01.png", "star_02.png", "dmag_vs_rms.png", "field_neb.png"} <= files
    assert all((tmp_path / "NEB" / n).read_bytes()[:4] == b"\x89PNG" for n in ("star_01.png", "field_neb.png"))


def test_dmag_vs_rms_boundary_lines(tmp_path):
    """The summary plot carries the 5 and 3 boundary lines, drawn from the target depth the rows imply."""
    import matplotlib.pyplot as plt

    from astrowb.photometry import neb
    from astrowb.photometry.reports import neb_plots

    seen = []
    orig = neb_plots._save
    neb_plots._save = lambda fig, path: seen.append(fig) or orig(fig, path)
    try:
        row = {
            "name": "1",
            "disposition": "Cleared",
            "dmag": 3.0,
            "required_ppt": neb.required_depth_ppt(10.0, 3.0),
            "rms_ppt": 1.0,
        }
        neb_plots.write(tmp_path, [row])
    finally:
        neb_plots._save = orig
    ax = seen[-1].axes[0]
    line = next(ln for ln in ax.get_lines() if ln.get_label() == "depth needed / RMS = 5")
    x, y = line.get_data()
    assert np.allclose(y, neb.required_depth_ppt(10.0, x) / 5)
    plt.close("all")


def _stars():
    # target, a pair 6 px apart (3 ″ at 0.5 ″/px... scale 2 below), a lone star
    return {"x": [10.0, 60.0, 66.0, 60.0], "y": [10.0, 60.0, 60.0, 20.0], "gmag": [10.0, 12.0, 12.5, 12.0]}


def test_neighbours_of_a_star():
    from astrowb.photometry.neb import _neighbours

    st = {k: np.asarray(v) for k, v in _stars().items()}
    a = _neighbours(st["x"], st["y"], st["gmag"], 1.0, 1, 0)
    assert a["nearest_px"] == 6.0 and a["close"] == ["G12.5 @ 6.0″"]
    b = _neighbours(st["x"], st["y"], st["gmag"], 1.0, 3, 0)
    assert b["nearest_px"] == 40.0 and b["close"] == []


def test_run_rows_carry_neighbours_and_crowded_label_is_red(tmp_path, monkeypatch):
    from astrowb.photometry import neb
    from astrowb.photometry.reports import neb_plots

    n = 20
    flux = {"target_flux": np.full(n, 1e6), "jd_utc": 2460000 + np.arange(n) / 100.0,
            "extra_flux": np.full((n, 3), 4e4)}  # fmt: skip
    monkeypatch.setattr("astrowb.photometry.lightcurve.light_curve", lambda *a, **k: flux)
    field = {"scale": 1.0, "stars": _stars()}
    rows = neb.run([], (10, 10), [], field, 5.0, 3.0, 5.0, 8.0, 100.0)
    crowded = next(r for r in rows if r["x"] == 60.0 and r["y"] == 60.0)
    assert crowded["r_ap"] == 3.0 and crowded["nearest_px"] <= 3 * crowded["r_ap"]
    assert next(r for r in rows if r["y"] == 20.0)["nearest_px"] > 9
    import json

    json.dumps(rows)
    seen = []
    monkeypatch.setattr(neb_plots, "_save", lambda fig, path: seen.append(fig))
    neb_plots._field(tmp_path / "f.png", rows, np.ones((80, 80)), (10, 10))
    colours = {t.get_text(): t.get_color() for t in seen[-1].axes[0].texts}
    assert colours["2"] == "red" and colours["1"] != "red"  # numbered nearest first: the lone star is 1


def test_best_aperture_wins(monkeypatch):
    from astrowb.photometry import neb

    row = lambda d, r: {"x": 1.0, "y": 2.0, "disposition": d, "r_ap": r, "separation": 5.0}  # noqa: E731
    calls = iter([[row("Not cleared", 3.0)], [row("Cleared", 6.0)]])
    monkeypatch.setattr(neb, "run", lambda *a, **k: next(calls))
    out = neb.run_apertures([], (0, 0), [], {}, 5.0, [(3.0, 5.0, 8.0), (6.0, 9.0, 12.0)])
    assert len(out) == 1 and out[0]["disposition"] == "Cleared" and out[0]["r_ap"] == 6.0
    assert [a["disposition"] for a in out[0]["apertures"]] == ["Not cleared", "Cleared"]


def test_step_apertures_param(monkeypatch):
    """The step: no apertures = neb.run as before; given = neb.run_apertures with the triples."""
    from astrowb.engine.steps import REGISTRY
    from astrowb.photometry import fit_steps  # noqa: F401  registers the step

    seen, run = {}, REGISTRY["photometry.neb_check"].func
    monkeypatch.setattr(neb, "run", lambda *a, **k: seen.setdefault("run", a) and [])
    monkeypatch.setattr(neb, "run_apertures", lambda *a, **k: seen.setdefault("many", a) and [])
    inputs = {"images": ["a"], "target_xy": [1, 2], "comps_xy": [[3, 4]], "field": {}}
    params = {"depth_ppt": 5.0, "radius_arcsec": 100.0, "r_ap": 5.0, "r_in": 8.0, "r_out": 12.0}
    run(inputs, params, None)
    assert "many" not in seen and seen["run"][5:8] == (5.0, 8.0, 12.0)
    run(inputs, params | {"apertures": [[3, 5, 8], [6, 9, 12]]}, None)
    assert seen["many"][5] == [(3, 5, 8), (6, 9, 12)]
