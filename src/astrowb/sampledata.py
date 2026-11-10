"""A practice night: simulated raw frames of an eclipsing binary through a primary minimum, with the bias,
dark and flat frames to calibrate them. The truth (time of minimum, star positions) is returned and written
to truth.json, so a learner can check every step of the tutorial in the Guide."""

import json
from pathlib import Path

import numpy as np

SHAPE = (160, 200)
TARGET = (100.0, 80.0)  # x, y of the eclipsing binary in the first frame (0-based pixels)
COMPS = ((40.0, 50.0), (160.0, 110.0), (60.0, 130.0))
RA, DEC = "02:04:10.3", "+46:41:16"
T_MIN_JD = 2461000.40  # UTC JD of mid-eclipse


def make(folder, n_lights=48, seed=7):
    """Writes raw/*.fits and truth.json into folder; returns the truth."""
    import astropy.units as u
    from astropy.io import fits
    from astropy.time import Time

    rng = np.random.default_rng(seed)
    raw = Path(folder) / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    yy, xx = np.mgrid[: SHAPE[0], : SHAPE[1]]
    bias, dark_rate, gain = 300.0, 2.0, 1.0
    flat = 1.0 - 0.25 * ((xx - 100) ** 2 + (yy - 80) ** 2) / (100**2 + 80**2)  # vignetting
    base = {"OBJECT": "PRACTICE", "OBJCTRA": RA, "OBJCTDEC": DEC, "SITELAT": 36.82, "SITELONG": 30.34}
    base |= {"SITEELEV": 2500.0, "XBINNING": 1, "YBINNING": 1, "CCD-TEMP": -10.0, "GAIN": gain}

    def write(name, data, kind, exptime, extra=None):
        h = fits.Header(base | {"IMAGETYP": kind, "EXPTIME": exptime} | (extra or {}))
        fits.PrimaryHDU(np.clip(data, 0, 65535).astype(np.float32), h).writeto(raw / name, overwrite=True)

    noise = lambda img: rng.poisson(np.clip(img, 0, None)).astype(float) + rng.normal(0, 5, SHAPE)  # noqa: E731
    for i in range(7):
        write(f"bias_{i:02d}.fits", bias + rng.normal(0, 5, SHAPE), "Bias Frame", 0.0)
        write(f"dark_{i:02d}.fits", noise(np.full(SHAPE, dark_rate * 60)) + bias, "Dark Frame", 60.0)
        write(f"flat_V_{i:02d}.fits", noise(20000 * flat) + bias, "Flat Field", 2.0, {"FILTER": "V"})
    t0 = Time(T_MIN_JD - n_lights / 2 * 150 / 86400, format="jd", scale="utc")
    for i in range(n_lights):
        start = t0 + i * 150 * u.s
        mid = start.jd + 30 / 86400
        depth = 0.45 * np.exp(-0.5 * ((mid - T_MIN_JD) / 0.012) ** 2)  # primary eclipse
        dx, dy = 0.04 * i, -0.03 * i  # slow drift
        sky = np.full(SHAPE, 150.0)
        for (x, y), f in zip((TARGET, *COMPS), (30000 * (1 - depth), 40000, 25000, 35000), strict=True):
            sky += f / (2 * np.pi * 2.0**2) * np.exp(-((xx - x - dx) ** 2 + (yy - y - dy) ** 2) / (2 * 2.0**2))
        light = noise(sky * flat + dark_rate * 60) + bias
        write(f"light_V_{i:03d}.fits", light, "Light Frame", 60.0, {"FILTER": "V", "DATE-OBS": start.isot})
    from astropy.coordinates import EarthLocation, SkyCoord

    from . import timing

    site = EarthLocation.from_geodetic(30.34 * u.deg, 36.82 * u.deg, 2500 * u.m)
    bjd = timing.bjd_tdb(Time(T_MIN_JD, format="jd", scale="utc"), SkyCoord(RA, DEC, unit=(u.hourangle, u.deg)), site)
    truth = {"t_min_jd_utc": T_MIN_JD, "t_min_bjd_tdb": float(bjd.jd), "target_xy": list(TARGET)}
    truth["comps_xy"] = [list(c) for c in COMPS]
    truth |= {"ra": RA, "dec": DEC, "depth": 0.45}
    (Path(folder) / "truth.json").write_text(json.dumps(truth, indent=1), encoding="utf-8")
    return truth
