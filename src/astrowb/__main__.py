"""Entry point. ``--smoke-test DIR`` opens and saves a FITS file headlessly (used by CI on installed builds)."""

import argparse
import multiprocessing
import os
import sys
import traceback
from pathlib import Path


def smoke_test(workdir: Path) -> None:
    """Exercise the installed app end to end: GUI window, FITS open, save via worker process, project file."""
    import astropy.units as u
    import numpy as np
    from astropy.io import fits

    from . import selfcheck
    from .ui.main_window import MainWindow

    failed = [r for r in selfcheck.offline() if not r[1]]  # every module, library and shipped data file
    assert not failed, selfcheck.report(failed)

    workdir.mkdir(parents=True, exist_ok=True)
    src, dst = workdir / "smoke_in.fits", workdir / "smoke_out.fits"
    data = np.arange(120 * 100, dtype=np.float32).reshape(100, 120)
    fits.PrimaryHDU(data, fits.Header({"OBJECT": "SMOKE"})).writeto(src, overwrite=True)

    win = MainWindow()
    win.show()
    win.open_project(workdir / "smoke.astroproj")
    assert win.open_fits(src), "open failed"
    win.save_as(dst).result(timeout=120)
    with fits.open(dst) as hdul:
        assert hdul[0].header["OBJECT"] == "SMOKE"
        assert np.array_equal(hdul[0].data, data)
    assert len(win.engine.project.files()) == 1

    # calibration (incl. compiled astroscrappy) and photometry (photutils) in a worker process
    raw = workdir / "raw"
    raw.mkdir(exist_ok=True)
    rng = np.random.default_rng(0)
    yy, xx = np.mgrid[:64, :64]
    star = 5000 * np.exp(-((xx - 32) ** 2 + (yy - 30) ** 2) / 4.5)
    for i in range(3):
        fits.PrimaryHDU(rng.normal(300, 5, (64, 64)).astype(np.float32), fits.Header({"IMAGETYP": "BIAS"})).writeto(
            raw / f"b{i}.fits", overwrite=True
        )
        light = 300 + 100 + star + np.roll(star, 15, axis=1) + rng.normal(0, 5, (64, 64))
        fits.PrimaryHDU(
            light.astype(np.float32),
            fits.Header({"IMAGETYP": "LIGHT", "EXPTIME": 10.0, "DATE-OBS": f"2026-01-01T00:0{i}:00"}),
        ).writeto(raw / f"l{i}.fits", overwrite=True)
    out = win.engine.run_chain(
        ["calibration.scan", "calibration.run"],
        {"folder": str(raw), "output_dir": str(workdir / "cal")},
        {"calibration.run": {"cosmic_rays": True}},
    )
    assert len(out["calibrated"]) == 3
    from astropy.coordinates import AltAz, EarthLocation, SkyCoord
    from astropy.time import Time

    from .core import earth_orientation
    from .engine import automation  # ready automation templates are bundled and refer to existing steps

    earth_orientation.configure()  # an installation years old still computes altitudes (ARC-1)
    later = Time.now() + 3 * 365 * u.day
    site = EarthLocation.from_geodetic(30 * u.deg, 39 * u.deg, 1000 * u.m)
    alt = SkyCoord(10 * u.deg, 20 * u.deg).transform_to(AltAz(obstime=later, location=site))
    assert abs(alt.alt.deg) <= 90
    templates = [a for a in automation.available() if a["template"]]
    assert len(templates) >= 5 and all(set(automation.needed(a)) <= set(a["inputs"]) for a in templates)
    from .ui import guide_page  # training pages are bundled in every language
    from .ui.i18n import LANGUAGES

    assert all(len(guide_page.load(lang)) == len(guide_page.load("en")) >= 12 for lang in LANGUAGES)
    assert all((guide_page.GUIDE / "images" / lang).is_dir() for lang in LANGUAGES)
    lc = win.engine.run_step(
        "photometry.light_curve", {"images": out["calibrated"], "target_xy": [32, 30], "comps_xy": [[47, 30]]}, {}
    ).result(timeout=120)
    assert abs(lc["light_curve"]["rel_flux"][0] - 1) < 0.05
    night = win.engine.run_step(  # planning: built-in ephemeris and astroquery are bundled; no network needed
        "planning.night",
        {
            "site": {"name": "", "lat": 37.0, "lon": 30.0, "height": 0.0},
            "date": "2026-11-15",
            "targets": [{"name": "t", "ra": 31.04, "dec": 46.69, "t0": 2455867.4027, "period": 2.15}],
        },
        {},
    ).result(timeout=300)
    assert night["night"]["dusk"] is not None
    from .planning import targets

    assert targets.parse_coordinates("02:04:10 +46:41:16") is not None

    # spectroscopy: a 2-D frame with a spectrum along row 20 is extracted; the line lists are bundled
    spec2d = rng.normal(100, 3, (40, 300)) + 5000 * np.exp(-0.5 * ((np.arange(40)[:, None] - 20) / 2) ** 2)
    fits.PrimaryHDU(spec2d.astype(np.float32)).writeto(workdir / "spec2d.fits", overwrite=True)
    spec = win.engine.run_step("spectroscopy.reduce", {"science": str(workdir / "spec2d.fits")}, {}).result(timeout=120)
    assert len(spec["spectrum"]["flux"]) == 300
    from .spectroscopy import wavecal

    assert len(wavecal.load_line_list("henear")) > 50

    # binary-star model fit through a worker process
    from .models import fit as ebfit

    eb_truth = {"period": 1.5, "t0": 0.3, "r_sum": 0.3, "k": 0.7, "incl": 87.0, "j": 0.6}
    eb_truth |= {"ecosw": 0.0, "esinw": 0.0, "l3": 0.0}
    tt = np.linspace(0, 3, 900)
    lc_path = workdir / "eb.csv"
    lc_path.write_text(
        "time,rel_flux\n" + "\n".join(f"{a},{b}" for a, b in zip(tt, ebfit.model(tt, eb_truth), strict=True))
    )
    model = win.engine.run_step("models.eb_fit", {"light_curve": str(lc_path), "start": eb_truth}, {})
    assert abs(model.result(timeout=120)["model"]["params"]["incl"] - 87.0) < 0.1

    # remote sensing: GeoTIFF with georeferencing through a worker; PROJ data bundled for lat/lon
    import tifffile

    from .remotesensing import raster

    geo = [(33550, "d", 3, (30.0, 30.0, 0.0), True), (33922, "d", 6, (0, 0, 0, 500000.0, 4100000.0, 0), True)]
    geo.append((34735, "H", 8, (1, 1, 0, 1, 3072, 0, 1, 32635), True))
    tifffile.imwrite(
        workdir / "rs.tif", rng.random((2, 20, 30)).astype(np.float32), planarconfig="separate", extratags=geo
    )
    prod = win.engine.run_step("rs.expression", {"raster": str(workdir / "rs.tif"), "expression": "B1 - B2"}, {})
    prod = raster.read(prod.result(timeout=120)["product"]["path"])
    assert prod.epsg == 32635 and abs(prod.lonlat(15, 10)[0] - 27.0) < 0.1
    import h5py  # HDF5 / NetCDF-4 and JPEG2000 readers are bundled
    import imagecodecs

    with h5py.File(workdir / "rs.h5", "w") as f:
        f["band"] = np.ones((8, 9), np.float32)
    assert raster.read(workdir / "rs.h5").shape == (8, 9)
    (workdir / "rs.jp2").write_bytes(imagecodecs.jpeg2k_encode(np.ones((8, 9), np.uint16), level=0))
    assert raster.read(workdir / "rs.jp2").shape == (8, 9)
    import rawpy  # DSLR raw files: LibRaw's shared library is in the bundle

    assert rawpy.libraw_version >= (0, 20)

    # observatory API (no devices) and the Alpaca client are in the bundle
    import alpaca.telescope  # noqa: F401

    from .devices.server import Client, Controller, build, serve

    obs, _ = build({"site": {"lat": 37.0, "lon": 30.0}})
    server = serve(Controller(obs), "smoke", port=0)
    assert Client(f"http://127.0.0.1:{server.server_address[1]}", "smoke").status()["safe"]
    server.shutdown()
    win.close()

    # GPU path (or its CPU fallback) must load and agree with the CPU in the installed build
    from . import compute
    from .compute.combine import clipped_mean

    previous = compute.mode()
    compute.set_mode("gpu")
    stack = np.random.default_rng(0).normal(100, 5, (8, 64, 64)).astype(np.float32)
    img, _, used = clipped_mean(stack, use_gpu=True)
    print(f"compute: {compute.describe()} -> ran on {used}")
    compute.set_mode(previous)
    ref, _, _ = clipped_mean(stack, use_gpu=False)
    assert np.allclose(img, ref, rtol=1e-4), "GPU and CPU disagree"


def _show_unexpected_errors(settings):
    """An error nobody caught (in a button's handler) is shown, and kept in error.log in the settings folder,
    instead of only being printed where no user sees it: a button that "does nothing" is worse than a message."""
    import datetime

    from PySide6.QtWidgets import QApplication, QMessageBox

    log = settings.path.parent / "error.log"

    def hook(kind, value, tb):
        text = "".join(traceback.format_exception(kind, value, tb))
        try:
            with log.open("a", encoding="utf-8") as f:
                f.write(f"--- {datetime.datetime.now().isoformat(timespec='seconds')}\n{text}\n")
        except OSError:  # a read-only settings folder must not hide the message
            pass
        sys.__stderr__ and sys.__stderr__.write(text)
        if QApplication.instance():
            title = QApplication.translate("App", "Unexpected error")
            box = QMessageBox(QMessageBox.Critical, title, f"{kind.__name__}: {value}")
            box.setDetailedText(text)
            box.exec()

    sys.excepthook = hook


def main(argv=None) -> int:
    multiprocessing.freeze_support()  # required for worker processes in frozen (installed) builds
    if getattr(sys, "frozen", False) and "SSL_CERT_FILE" not in os.environ:
        # the bundled OpenSSL looks for certificates where the build machine keeps them, which is not where
        # every system keeps them: HTTPS (SIMBAD, VizieR, MAST, ...) failed on Arch. Use the bundled list.
        import certifi

        os.environ["SSL_CERT_FILE"] = certifi.where()  # worker processes inherit it
    words = sys.argv[1:] if argv is None else list(argv)
    if words and words[0] in ("steps", "help", "run", "recipe"):  # the command line without a window (ARC-12)
        from .cli import main as cli_main

        return cli_main(words)
    return _app(argv)


def _app(argv) -> int:
    """The window, or one of the options that run without it (--smoke-test, --benchmark, …)."""
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="*", type=Path, help="FITS files or a project to open")
    parser.add_argument("--smoke-test", type=Path, metavar="DIR")
    parser.add_argument("--benchmark", action="store_true", help="time CPU vs GPU and exit")
    parser.add_argument(
        "--check-online", action="store_true", help="check the installation and every web service it uses, and exit"
    )
    parser.add_argument("--observatory", type=Path, metavar="CONFIG", help="run the observatory process (no window)")
    args = parser.parse_args(argv)

    from . import compute
    from .settings import Settings

    settings = Settings()
    if compute.MODE_ENV not in os.environ:  # worker processes inherit the choice through the environment
        compute.set_mode(settings.get("compute.device", "auto"))
    if args.observatory:
        from .devices.server import main as observatory_main

        observatory_main(args.observatory)
        return 0
    if args.check_online:
        from . import selfcheck

        results = selfcheck.offline() + selfcheck.online()
        text = selfcheck.report(results)
        out = settings.path.parent / "check-online.txt"
        try:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text + "\n", encoding="utf-8")
        except OSError:  # a read-only settings folder: the report is still shown
            pass
        if sys.stdout is not None:
            print(text)
            print(f"(saved in {out})")
        else:  # the Windows and macOS applications have no console: show the report in a window
            from PySide6.QtWidgets import QApplication, QMessageBox

            app = QApplication.instance() or QApplication(sys.argv[:1])
            box = QMessageBox(QMessageBox.Information, "--check-online", f"{text}\n\n{out}")
            box.setStyleSheet("QLabel { font-family: monospace; }")
            box.exec()
        return 0 if all(ok for _, ok, _ in results) else 1
    if args.benchmark:
        from .compute.check import benchmark

        text = "\n".join(benchmark())
        out = settings.path.parent / "gpu-check.txt"
        try:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text + "\n", encoding="utf-8")
        except OSError:  # a read-only settings folder: the report is still shown
            pass
        if sys.stdout is not None:
            print(text)
            print(f"(saved in {out})")
        else:  # the Windows and macOS applications have no console: show the report in a window
            from PySide6.QtWidgets import QApplication, QMessageBox

            app = QApplication.instance() or QApplication(sys.argv[:1])
            box = QMessageBox(QMessageBox.Information, "--benchmark", f"{text}\n\n{out}")
            box.setStyleSheet("QLabel { font-family: monospace; }")
            box.exec()
        return 0

    from PySide6.QtWidgets import QApplication

    from .brand import BRAND
    from .settings import migrate_previous
    from .ui import i18n

    migrate_previous()
    app = QApplication(sys.argv[:1])
    app.setApplicationName(BRAND.display_name)
    app.setOrganizationName(BRAND.organization)
    app.setApplicationDisplayName(BRAND.display_name)
    if sys.platform == "linux":
        app.setDesktopFileName(BRAND.app_id)
    from .ui import theme

    theme.apply(app, settings.get("ui.theme", theme.DEFAULT), theme.font_size(settings))
    if not args.smoke_test:
        from .ui.welcome import first_run

        chosen = first_run(app, settings)
        if chosen:
            theme.apply(app, chosen["ui.theme"], theme.font_size(settings))
            if compute.MODE_ENV not in os.environ:
                compute.set_mode(chosen["compute.device"])
    language = settings.get("ui.language") or i18n.system_language()
    translators = i18n.install(app, language)  # noqa: F841  (must stay alive)

    if args.smoke_test:
        args.smoke_test.mkdir(parents=True, exist_ok=True)
        result = args.smoke_test / "smoke-result.txt"
        try:
            smoke_test(args.smoke_test)
            result.write_text("OK\n")
            print("smoke test OK")
            return 0
        except Exception:
            result.write_text(traceback.format_exc())
            traceback.print_exc()
            return 1

    from .ui.main_window import MainWindow

    _show_unexpected_errors(settings)
    win = MainWindow(settings)
    area = app.primaryScreen().availableGeometry()  # never larger than the screen, and on it
    win.resize(min(1500, int(area.width() * 0.92)), min(950, int(area.height() * 0.9)))
    win.move(area.center() - win.rect().center())
    for f in args.files:
        win.open_project(f) if f.suffix == ".astroproj" else win.open_fits(f, ask=True)
    win.show()
    from PySide6.QtCore import QTimer

    from .core import earth_orientation

    if not settings.get("ui.tour_done"):
        QTimer.singleShot(600, win.start_tour)  # once, after the first start
    if settings.get("time.auto_refresh", True) and earth_orientation.due():  # weekly, quietly, when allowed
        QTimer.singleShot(8000, lambda: win.update_time_tables(quiet=True))
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
