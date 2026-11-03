"""Time every main operation on synthetic data of a real camera's size (PLAN 4.8 item 12).

    python tools/speed.py [--size 4096] [--out speed.md]

Each operation runs as the engine step the application runs (in this process, so the time is the step's own,
without starting a worker). The data are made here with stars, sky and noise; nothing is downloaded. The results
are a Markdown table. Spectroscopy timings come from its tests (see --spectra).
"""

import argparse
import tempfile
import time
from pathlib import Path

import numpy as np
from astropy.io import fits


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


def timed(rows, label, fn):
    t = time.perf_counter()
    out = fn()
    rows.append((label, time.perf_counter() - t))
    print(f"{label}: {rows[-1][1]:.2f} s", flush=True)
    return out


def main():
    from astrowb.engine import builtin  # noqa: F401  (registers the steps)
    from astrowb.engine.steps import execute
    from astrowb.io.fits import read_image

    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=4096, help="frame side in pixels (4096 = 16.8 megapixels)")
    ap.add_argument("--lights", type=int, default=10)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    size, n = args.size, args.lights
    rng = np.random.default_rng(1)
    rows = []
    ctx = Ctx()
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "raw"
        raw.mkdir()
        bias = rng.normal(500, 5, (size, size)).astype(np.float32)
        for i in range(5):
            h = fits.Header({"IMAGETYP": "Bias", "EXPTIME": 0.0})
            fits.PrimaryHDU((bias + rng.normal(0, 5, bias.shape)).astype(np.uint16), h).writeto(raw / f"b{i}.fits")
            h = fits.Header({"IMAGETYP": "Dark", "EXPTIME": 60.0, "CCD-TEMP": -10.0})
            fits.PrimaryHDU((bias + rng.normal(20, 5, bias.shape)).astype(np.uint16), h).writeto(raw / f"d{i}.fits")
            h = fits.Header({"IMAGETYP": "Flat", "EXPTIME": 2.0, "FILTER": "V"})
            fits.PrimaryHDU((bias + rng.normal(20000, 140, bias.shape)).astype(np.uint16), h).writeto(
                raw / f"f{i}.fits"
            )
        comps = None
        for i in range(n):
            img, xy = stars_image(rng, size, shift=(0.7 * i, -0.4 * i))
            comps = comps or xy
            h = fits.Header({"IMAGETYP": "Light", "EXPTIME": 60.0, "CCD-TEMP": -10.0, "FILTER": "V"})
            h["DATE-OBS"] = f"2026-11-15T20:{i:02d}:00"
            fits.PrimaryHDU(np.clip(img + bias, 0, 65535).astype(np.uint16), h).writeto(raw / f"l{i:02d}.fits")

        timed(rows, f"Open a {size}x{size} FITS", lambda: read_image(raw / "l00.fits"))
        frames = timed(
            rows, "Scan the folder (headers)", lambda: execute("calibration.scan", {"folder": str(raw)}, {}, ctx)
        )
        cal = timed(
            rows,
            f"Calibrate: 3 masters of 5 + {n} lights",
            lambda: execute(
                "calibration.run", {"frames": frames["frames"], "output_dir": str(Path(tmp) / "cal")}, {}, ctx
            ),
        )
        lights = sorted(cal["calibrated"])
        for align in ("translation", "stars"):
            timed(
                rows,
                f"Stack {n} lights (sigma clip, align: {align})",
                lambda a=align: execute(
                    "stacking.stack", {"images": lights, "output": str(Path(tmp) / f"s_{a}.fits")}, {"align": a}, ctx
                ),
            )
        timed(rows, f"Frame quality ({n} frames)", lambda: execute("photometry.quality", {"images": lights}, {}, ctx))
        target, cmps = comps[0], comps[1:]
        timed(
            rows,
            f"Light curve, 1 target + 3 comparisons ({n} frames, automatic apertures)",
            lambda: execute(
                "photometry.light_curve", {"images": lights, "target_xy": target, "comps_xy": cmps}, {}, ctx
            ),
        )
        for op in ("median", "unsharp", "rotate"):
            params = {"args": {"angle": 12.5}} if op == "rotate" else {}
            timed(
                rows,
                f"Image -> Process: {op}",
                lambda o=op, p=params: execute(
                    "image.process",
                    {"image": lights[0], "operation": o, "output": str(Path(tmp) / f"p_{o}.fits")},
                    p,
                    ctx,
                ),
            )

    # time series: a TESS-like light curve
    t = np.sort(rng.uniform(0, 27, 15000))
    flux = 1 - 0.3 * (np.abs(((t - 0.3) / 2.15 + 0.5) % 1 - 0.5) < 0.02) + rng.normal(0, 0.002, t.size)
    timed(
        rows,
        "Period search, 15 000 points (Lomb-Scargle)",
        lambda: execute("timeseries.period", {"time": t.tolist(), "flux": flux.tolist()}, {}, ctx),
    )
    timed(
        rows,
        "Frequency analysis, 15 000 points",
        lambda: execute("timeseries.frequencies", {"time": t.tolist(), "flux": flux.tolist()}, {}, ctx),
    )
    print("| Operation | Seconds |\n|---|---|", *[f"| {k} | {v:.2f} |" for k, v in rows], sep="\n")
    if args.out:
        Path(args.out).write_text(
            "\n".join(["| Operation | Seconds |", "|---|---|", *[f"| {k} | {v:.2f} |" for k, v in rows]]) + "\n"
        )


if __name__ == "__main__":
    main()
