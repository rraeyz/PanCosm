import numpy as np
from astropy.table import Table
from astropy.wcs import WCS

from astrowb import overlays


def make_wcs(rot_deg=20.0):
    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crval = [31.04, 46.69]
    w.wcs.crpix = [100.5, 80.5]
    s, c = np.sin(np.radians(rot_deg)), np.cos(np.radians(rot_deg))
    scale = 1.5 / 3600
    w.wcs.cd = scale * np.array([[-c, s], [s, c]])
    return w


def test_contour_of_a_gaussian_is_a_circle():
    yy, xx = np.mgrid[:100, :120]
    img = 10 + 1000 * np.exp(-((xx - 60) ** 2 + (yy - 40) ** 2) / (2 * 5.0**2))
    img += np.random.default_rng(0).normal(0, 1, img.shape)
    lines = overlays.contours(img, [10 + 1000 * np.exp(-0.5 * 2**2)], smooth=0)  # level at r = 2 sigma = 10 px
    (line,) = next(iter(lines.values()))
    r = np.hypot(np.asarray(line)[:, 0] - 60, np.asarray(line)[:, 1] - 40)
    assert abs(r.mean() - 10) < 0.2 and r.std() < 0.2
    levels = overlays.contour_levels(img, 5)
    assert len(levels) == 5 and levels[0] > 12 and levels[-1] < img.max()


def test_wcs_grid_lines_follow_constant_coordinates():
    w = make_wcs()
    grid = overlays.wcs_grid(w, (160, 200))
    kinds = {k for k, *_ in grid}
    assert kinds == {"ra", "dec"} and len(grid) >= 4
    for kind, value, line, label in grid:
        x, y = np.asarray(line).T
        sky = w.pixel_to_world(x, y)
        got = sky.ra.deg if kind == "ra" else sky.dec.deg
        assert np.allclose(got, value, atol=1e-6) and label


def test_catalogue_to_pixels():
    w = make_wcs()

    def fake(cat, ra, dec, radius, mag_col, mag_limit):
        assert cat == "I/355/gaiadr3"
        return Table({"Source": [1, 2], "_RAJ2000": [31.04, 40.0], "_DEJ2000": [46.69, 10.0], "Gmag": [12.5, 9.0]})

    stars = overlays.to_pixels(w, (160, 200), overlays.query_catalogue(31.04, 46.69, 0.1, query=fake))
    assert len(stars) == 1 and abs(stars[0]["x"] - 99.5) < 1e-6 and stars[0]["mag"] == 12.5


def test_ds9_regions_round_trip_and_parse():
    w = make_wcs()
    regs = [{"shape": "circle", "x": 50.0, "y": 60.0, "r": 8.0, "text": "T"}, {"shape": "point", "x": 10.0, "y": 20.0}]
    for wcs in (None, w):
        back = overlays.read_regions(overlays.write_regions(regs, wcs), wcs)
        assert back[0]["shape"] == "circle" and back[0]["text"] == "T"
        assert abs(back[0]["x"] - 50) < 1e-3 and abs(back[0]["y"] - 60) < 1e-3 and abs(back[0]["r"] - 8) < 1e-3
        assert back[1]["shape"] == "point" and abs(back[1]["x"] - 10) < 1e-3
    ds9 = """# Region file format: DS9 version 4.1
global color=green dashlist=8 3 width=1
fk5
circle(2:04:09.600,+46:41:24.00,6") # text={star}
image
box(30,40,10,6,0)
line(1,1,11,11) # line=0 0
# text(20,30) text={label}
"""
    got = overlays.read_regions(ds9, w)
    assert [g["shape"] for g in got] == ["circle", "box", "line", "text"]
    assert abs(got[0]["r"] - 4.0) < 1e-6 and got[0]["text"] == "star"  # 6" at 1.5"/px
    assert (got[1]["x"], got[1]["w"]) == (29.0, 10.0) and got[2]["x2"] == 10.0 and got[3]["text"] == "label"
    assert overlays.read_regions(ds9, None)[0]["shape"] == "box"  # sky regions need a WCS


def test_overlay_menu_actions(qtbot, tmp_path):
    from astropy.io import fits

    from astrowb.settings import Settings
    from astrowb.ui import overlay_actions as oa
    from astrowb.ui.main_window import MainWindow

    yy, xx = np.mgrid[:160, :200]
    img = (
        100
        + 5000 * np.exp(-((xx - 99.5) ** 2 + (yy - 79.5) ** 2) / 8)
        + np.random.default_rng(0).normal(0, 3, xx.shape)
    )
    path = tmp_path / "solved.fits"
    fits.PrimaryHDU(img.astype(np.float32), make_wcs().to_header()).writeto(path)
    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    try:
        win.open_fits(path)
        assert oa.contours(win, 4) >= 1 and oa.grid(win) >= 4
        oa.show_catalogue(win, "gaia", [{"name": "1", "ra": 31.04, "dec": 46.69, "mag": 12.0, "x": 99.5, "y": 79.5}])
        assert win.viewer.overlay_names() == ["contours", "gaia", "grid"]
        from PySide6.QtWidgets import QGraphicsSimpleTextItem

        def names():
            return sorted(i.text() for i in win.viewer.scene().items() if isinstance(i, QGraphicsSimpleTextItem))

        crowd = [{"name": f"V{i}", "mag": None, "x": 5.0 + 4 * i, "y": 20.0} for i in range(40)]
        oa.show_catalogue(win, "vsx", crowd)  # 40 names hid the field (interface I6b (1)): each on hover instead
        assert "V3" not in names() and any(i.toolTip() == "V3" for i in win.viewer.scene().items())
        win.viewer.set_markers([(99.5, 79.5, 6, "yellow", "T"), (20.0, 20.0, 9, "cyan", "VSX 1", "dash", "quiet")])
        assert "T" in names() and "VSX 1" not in names()
        saved = oa.save_regions(win, str(tmp_path / "m.reg"))
        assert "fk5" in open(saved).read()
        regs = oa.load_regions(win, saved)
        assert abs(regs[0]["x"] - 99.5) < 1e-3 and abs(regs[0]["r"] - 6) < 1e-3
        win.open_fits(path)  # a new image clears the overlays
        assert win.viewer.overlay_names() == []
    finally:
        win.engine.shutdown()


def test_finder_chart_from_an_image_and_from_dss(tmp_path, monkeypatch):
    from astropy.io import fits

    from astrowb.engine.steps import execute

    class Ctx:
        def progress(self, *a):
            pass

    w = make_wcs(0.0)
    yy, xx = np.mgrid[:160, :200]
    img = 100 + 3000 * np.exp(-((xx - 60) ** 2 + (yy - 50) ** 2) / 6) + np.random.default_rng(1).normal(0, 3, xx.shape)
    path = tmp_path / "solved.fits"
    fits.PrimaryHDU(img.astype(np.float32), w.to_header()).writeto(path)
    ra, dec = w.pixel_to_world_values(60, 50)

    def fake_query(ra0, dec0, radius, catalogue, mag_limit):
        return [{"name": "1", "ra": float(ra), "dec": float(dec), "mag": 11.0, "v": 11.24}]

    monkeypatch.setattr(overlays, "query_catalogue", fake_query)
    out = execute("image.finder_chart", {"image": str(path), "output": str(tmp_path / "chart.png")}, {}, Ctx())
    assert out["labelled"] == 1 and (tmp_path / "chart.png").stat().st_size > 10000
    monkeypatch.setattr(overlays, "dss_image", lambda ra, dec, fov: (img, w))
    out = execute("image.finder_chart", {"ra": 31.04, "dec": 46.69, "output": str(tmp_path / "dss.png")}, {}, Ctx())
    assert (tmp_path / "dss.png").exists()

    def offline(*a):
        raise OSError("no network")

    monkeypatch.setattr(overlays, "query_catalogue", offline)
    out = execute("image.finder_chart", {"image": str(path), "output": str(tmp_path / "c2.png")}, {}, Ctx())
    assert out["labelled"] == 0 and (tmp_path / "c2.png").exists()


def test_finder_chart_menu(qtbot, tmp_path, monkeypatch):
    from astropy.io import fits

    from astrowb.settings import Settings
    from astrowb.ui import overlay_actions as oa
    from astrowb.ui.main_window import MainWindow

    monkeypatch.setattr(overlays, "query_catalogue", lambda *a: [])
    path = tmp_path / "solved.fits"
    fits.PrimaryHDU(
        np.random.default_rng(0).normal(100, 3, (160, 200)).astype(np.float32), make_wcs().to_header()
    ).writeto(path)
    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    shown = []
    monkeypatch.setattr(win, "show_picture", shown.append)

    class Ctx:
        def progress(self, *a):
            pass

    def run_here(step_id, inputs, params=None, on_done=None):  # in this process, where the catalogue is faked:
        from astrowb.engine.steps import execute  # a worker would query VizieR (slow or blocked in CI)

        on_done(execute(step_id, inputs, params or {}, Ctx()))

    monkeypatch.setattr(win, "run_step", run_here)
    try:
        win.open_fits(path)
        oa.finder_chart(win, output=str(tmp_path / "c.png"))
        assert shown and shown[0].endswith("c.png")
    finally:
        win.engine.shutdown()


SKYBOT_ANSWER = """# Flag: 1
# Ticket: 188082858033461702
# Num | Name | RA(h) | DE(deg) | Class | Mv | Err(arcsec) | d(arcsec)
 - | 2021 VE23 | 02 04 9.6600 | +46 41 24.000 | MB>Middle | 22.1 | 0.001 | 108.358
 365870 | 2011 UO282 | 02 04 2.3241 | +46 40 45.405 | MB>Inner | 18.3 | 0.254 | 138.905
"""


def test_minor_planets_from_skybot(tmp_path):
    from astropy.io import fits

    from astrowb.engine.steps import execute

    class Ctx:
        def progress(self, *a):
            pass

    rows = overlays.parse_skybot(SKYBOT_ANSWER)
    assert [r["name"] for r in rows] == ["2021 VE23", "2011 UO282"] and rows[1]["number"] == "365870"
    assert abs(rows[0]["ra"] - 31.0402500) < 1e-6 and abs(rows[0]["dec"] - 46.69) < 1e-6 and rows[0]["mag"] == 22.1
    asked = []
    found = overlays.minor_planets(
        31.04, 46.69, 0.1, 2460981.5, 20.0, fetch=lambda url: asked.append(url) or SKYBOT_ANSWER
    )
    assert [f["name"] for f in found] == ["2011 UO282"] and "-ep=2460981.500000" in asked[0]  # 22.1 is too faint
    w = make_wcs()
    h = w.to_header()
    h["DATE-OBS"], h["EXPTIME"] = "2026-11-03T20:00:00", 60.0
    path = tmp_path / "solved.fits"
    fits.PrimaryHDU(np.zeros((160, 200), np.float32), h).writeto(path)
    orig = overlays.minor_planets
    try:
        overlays.minor_planets = lambda ra, dec, r, jd, mag: [
            {
                "name": "x",
                "ra": float(w.pixel_to_world_values(50, 60)[0]),
                "dec": float(w.pixel_to_world_values(50, 60)[1]),
                "mag": 15.0,
            }
        ]
        out = execute("image.minor_planets", {"image": str(path)}, {}, Ctx())["objects"]
    finally:
        overlays.minor_planets = orig
    assert len(out) == 1 and abs(out[0]["x"] - 50) < 1e-6 and abs(out[0]["y"] - 60) < 1e-6
