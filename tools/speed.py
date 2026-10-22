"""Speed harness: named cases bound to the performance budgets (plans/architecture.md ARC-23).

    python tools/speed.py run [--ci] [--out speed/2026-11-11-abc123.json]   # every case; --ci: small data
    python tools/speed.py compare A.json B.json                             # the differences, case by case
    python tools/speed.py check speed/baseline-ci.json result.json          # exit 1 when a case is > 1.5x slower

Data are generated here (stars, sky, noise); nothing is downloaded. Each case runs as the engine step the program
runs, in this process. A case's time is the best of three runs (one for the long ones), after a first run that measures
its memory: the peak of Python and NumPy allocations (tracemalloc, which slows them, so that run is not timed).
Cases under MIN_SECONDS are compared but never fail: their times are mostly noise on a shared CI machine.
"""

import argparse
import json
import platform
import subprocess
import sys
import tempfile
import time
import tracemalloc
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from astropy.io import fits

FACTOR = 1.5
MIN_SECONDS = 0.2


class Ctx:
    def progress(self, *a):
        pass

    def check(self):
        pass


def stars_image(rng, size, shift=(0.0, 0.0), n=300, sky=800.0):
    img = rng.normal(sky, 12, (size, size)).astype(np.float32)
    rng2 = np.random.default_rng(99)  # the same field in every frame
    xs, ys, flux = rng2.uniform(40, size - 40, n), rng2.uniform(40, size - 40, n), rng2.uniform(2e3, 2e5, n)
    s = 1.6
    for x, y, f in zip(xs + shift[0], ys + shift[1], flux, strict=True):
        x0, y0 = int(x), int(y)
        yy, xx = np.mgrid[y0 - 8 : y0 + 9, x0 - 8 : x0 + 9]
        img[y0 - 8 : y0 + 9, x0 - 8 : x0 + 9] += (
            f / (2 * np.pi * s * s) * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * s * s))
        )
    return img, list(zip(xs[:4] + shift[0], ys[:4] + shift[1], strict=True))


def night(folder, size, n, rng):
    """Bias, dark and flat frames (5 each) and n lights of a drifting field, as a camera writes them."""
    bias = rng.normal(500, 5, (size, size)).astype(np.float32)
    for i in range(5):
        for kind, level, exp in (("Bias", 0, 0.0), ("Dark", 20, 60.0), ("Flat", 20000, 2.0)):
            h = fits.Header({"IMAGETYP": kind, "EXPTIME": exp, "CCD-TEMP": -10.0, "FILTER": "V"})
            data = bias + rng.normal(level, 5 if kind != "Flat" else 140, bias.shape)
            fits.PrimaryHDU(data.astype(np.uint16), h).writeto(folder / f"{kind[0].lower()}{i}.fits")
    comps = None
    for i in range(n):
        img, xy = stars_image(rng, size, shift=(0.7 * i, -0.4 * i))
        comps = comps or xy
        h = fits.Header({"IMAGETYP": "Light", "EXPTIME": 60.0, "CCD-TEMP": -10.0, "FILTER": "V"})
        h["DATE-OBS"] = f"2026-11-15T20:{i:02d}:00"
        fits.PrimaryHDU(np.clip(img + bias, 0, 65535).astype(np.uint16), h).writeto(folder / f"l{i:02d}.fits")
    return comps


def cases(tmp, ci):
    """[(name, budget row, function, repeats[, set-up])] in the order they run (later cases use earlier results); a
    set-up runs before every call, untimed."""
    from astrowb.engine import builtin  # noqa: F401  (registers the steps)
    from astrowb.engine.steps import execute
    from astrowb.io.fits import read_image

    size, n = (1024, 5) if ci else (4096, 10)
    rng = np.random.default_rng(1)
    raw = Path(tmp) / "raw"
    raw.mkdir()
    comps = night(raw, size, n, rng)
    ctx, keep = Ctx(), {}

    def calibrate():
        frames = execute("calibration.scan", {"folder": str(raw)}, {}, ctx)
        out = execute("calibration.run", {"frames": frames["frames"], "output_dir": str(Path(tmp) / "cal")}, {}, ctx)
        keep["lights"] = sorted(out["calibrated"])

    def stack():
        execute("stacking.stack", {"images": keep["lights"], "output": str(Path(tmp) / "s.fits")}, {}, ctx)

    def light_curve():
        execute(
            "photometry.light_curve", {"images": keep["lights"], "target_xy": comps[0], "comps_xy": comps[1:]}, {}, ctx
        )

    def display():
        from astrowb import display as d

        d.render(read_image(raw / "l00.fits")[0], limits=(700, 2000))

    t = np.sort(rng.uniform(0, 27, 15000 if ci else 100_000))
    t_model = np.linspace(0, 10, 100_000)
    flux = 1 - 0.3 * (np.abs(((t - 0.3) / 2.15 + 0.5) % 1 - 0.5) < 0.02) + rng.normal(0, 0.002, t.size)

    def period():
        execute("timeseries.period", {"time": t.tolist(), "flux": flux.tolist()}, {}, ctx)

    def frequencies():
        execute("timeseries.frequencies", {"time": t.tolist(), "flux": flux.tolist()}, {}, ctx)

    big = np.linspace(0, 80, 1_000_000)

    def decimate():
        from astrowb.ui.plot import spec

        for k in range(30):  # a pan of 30 frames across a million points
            spec.decimate_line(big, np.sin(big), 10 + k, 50 + k, 1200)

    def table_sort():
        from astropy.table import Table

        from astrowb.core import table

        tab = Table({f"c{i}": rng.normal(size=1_000_000) for i in range(5)})
        np.argsort(np.asarray(tab["c0"])[table.select(tab, "c1 > 0")], kind="stable")

    def kepler():
        from astrowb.spectroscopy.orbit import eccentric_anomaly

        eccentric_anomaly(rng.uniform(0, 100, 1_000_000), 0.3)

    def eclipses():  # the transit row's shape: an eclipse model over 10^5 times (limb darkening, two stars)
        from astrowb.models.eb import light_curve as eb_curve

        eb_curve(t_model, 2.15, 0.3, 0.15, 0.1, 87.0, j=0.5, ld1=(0.4, 0.2), ld2=(0.4, 0.2))

    orders, width = (20, 1024) if ci else (70, 4096)
    rows = 20 + 14 * np.arange(orders)
    yy = np.arange(rows[-1] + 20)[:, None]
    frame = 50 + sum(2000 * np.exp(-0.5 * ((yy - r) / 1.5) ** 2) for r in rows) * np.ones((1, width))
    frame = frame + rng.normal(0, 5, frame.shape)
    coefs = [np.array([0.0, float(r)]) for r in rows]

    def echelle():
        from astrowb.spectroscopy.echelle import extract

        extract(frame, coefs, method="optimal")

    def close_main():
        main = keep.pop("main", None)
        if main is not None:
            main.engine.shutdown()
            main.close()

    def start_window():  # from source: the budget's "Start window visible" (< 1.0 s)
        import atexit
        import os

        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication

        from astrowb.settings import Settings
        from astrowb.ui.main_window import MainWindow

        keep["app"] = QApplication.instance() or QApplication([])
        atexit.register(close_main)
        import tempfile

        folder = Path(tempfile.mkdtemp(prefix="settings", dir=tmp))  # a fresh one each start (id() repeats)
        keep["main"] = MainWindow(Settings(folder))
        keep["main"].show()
        keep["app"].processEvents()

    def open_window():  # in a fresh start window: the budget's "Open an area window" (first time < 1.0 s)
        keep["main"].show_workspace("photometry")
        keep["app"].processEvents()

    # shortcut: tracemalloc sees Python's allocations, not Qt's widgets; measure the process size when this row
    # is checked against its 500 MB
    def six_windows():  # the budget's "six windows open" (< 500 MB without data)
        for key in ("calibrate", "image", "photometry", "timeseries", "spectroscopy", "plan"):
            keep["main"].show_workspace(key)
        keep["app"].processEvents()

    def fresh_main():
        close_main()
        start_window()

    return [
        (f"open a {size}x{size} FITS", "Show a frame", lambda: read_image(raw / "l00.fits"), 3),
        ("start window", "Start window visible", start_window, 1, close_main),
        ("open the Photometry window (first time)", "Open an area window", open_window, 1, fresh_main),
        ("six area windows open", "Memory of the interface process with six windows open", six_windows, 1, fresh_main),
        (f"display conversion {size}x{size}", "Show a frame", display, 3),
        (f"calibrate: 3 masters of 5 + {n} lights", "Calibrate", calibrate, 1),
        (f"stack {n} lights (sigma clip)", "Calibrate", stack, 1),
        (f"light curve, {n} frames, 4 stars", "Light curve", light_curve, 1),
        (f"period search, {t.size} points (Lomb-Scargle)", "Period search", period, 1),
        (f"frequency analysis, {t.size} points", "Period search", frequencies, 1),
        ("plot decimation, 30 pans of 10^6 points", "Any click that only changes the view", decimate, 3),
        ("table filter and sort, 10^6 rows", "Any click that only changes the view", table_sort, 3),
        ("Kepler's equation, 10^6 anomalies", "Roche / transit models (native)", kepler, 3),
        ("eclipse model, 10^5 times", "Exact transit model", eclipses, 3),
        (f"échelle extraction, {orders} orders × {width} px, optimal", "Échelle extraction", echelle, 1),
    ]


def machine():
    import os

    return {"system": platform.platform(), "python": platform.python_version(), "cores": os.cpu_count()}


def commit():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    except OSError:
        return ""


def run(ci, out):
    results = {}
    with tempfile.TemporaryDirectory() as tmp:
        for name, budget, fn, repeats, *setup in cases(tmp, ci):
            prepare = setup[0] if setup else (lambda: None)
            prepare()
            tracemalloc.start()  # a first run for the memory (tracing slows allocations: not timed), then the times
            fn()
            peak = tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()
            times = []
            for _ in range(repeats):
                prepare()
                t0 = time.perf_counter()
                fn()
                times.append(time.perf_counter() - t0)
            results[name] = {"seconds": round(min(times), 4), "peak_mb": round(peak / 1e6, 1), "budget": budget}
            print(f"{name}: {min(times):.3f} s, {peak / 1e6:.0f} MB", flush=True)
    doc = {"date": datetime.now(UTC).isoformat(timespec="seconds"), "commit": commit(), "ci": ci,
           "machine": machine(), "cases": results}  # fmt: skip
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    return doc


def compare(a, b):
    """[(case, seconds in a, seconds in b, ratio b / a)] for the cases both have."""
    ca, cb = a["cases"], b["cases"]
    return [
        (k, ca[k]["seconds"], cb[k]["seconds"], cb[k]["seconds"] / max(ca[k]["seconds"], 1e-9)) for k in ca if k in cb
    ]


def slower(baseline, result, factor=FACTOR):
    """The cases more than `factor` times slower than the baseline (cases under MIN_SECONDS never count)."""
    return [row for row in compare(baseline, result) if row[3] > factor and row[2] >= MIN_SECONDS]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--ci", action="store_true", help="small generated data (CI)")
    r.add_argument("--out")
    for name in ("compare", "check"):
        p = sub.add_parser(name)
        p.add_argument("a")
        p.add_argument("b")
    args = ap.parse_args(argv)
    if args.cmd == "run":
        run(args.ci, args.out)
        return 0
    a, b = (json.loads(Path(p).read_text(encoding="utf-8")) for p in (args.a, args.b))
    for case, ta, tb, ratio in compare(a, b):
        print(f"{ratio:5.2f}x  {ta:8.3f} s -> {tb:8.3f} s  {case}")
    if args.cmd == "check":
        bad = slower(a, b)
        for case, *_ in bad:
            print(f"SLOWER than {FACTOR}x the baseline: {case}")
        return 1 if bad else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
