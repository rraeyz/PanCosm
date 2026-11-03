"""Colour (Bayer) cameras and DSLR raw files: superpixel channels, calibration of the mosaic, raw conversion."""

from pathlib import Path

import numpy as np
import pytest
import tifffile
from astropy.io import fits
from astropy.wcs import WCS

from astrowb.io import bayer


def mosaic(r, g1, g2, b, pattern="RGGB"):
    """A mosaic from four known planes placed by the pattern (g1 is the first green in reading order)."""
    planes, greens = {"R": r, "B": b}, [g1, g2]
    m = np.zeros((2 * r.shape[0], 2 * r.shape[1]), np.float32)
    for k, c in enumerate(pattern):
        dy, dx = divmod(k, 2)
        m[dy::2, dx::2] = greens.pop(0) if c == "G" else planes[c]
    return m


def test_pattern_and_superpixels():
    rng = np.random.default_rng(1)
    r, g1, g2, b = (rng.uniform(0, 1000, (20, 30)).astype(np.float32) for _ in range(4))
    for pat in bayer.PATTERNS:
        ch = bayer.split(mosaic(r, g1, g2, b, pat), pat)
        assert np.array_equal(ch["R"], r) and np.array_equal(ch["B"], b) and np.allclose(ch["G"], (g1 + g2) / 2)
    assert bayer.pattern_of(fits.Header({"BAYERPAT": "RGGB"})) == "RGGB"
    assert bayer.pattern_of(fits.Header({"BAYERPAT": "RGGB", "XBAYROFF": 1})) == "GRBG"
    assert bayer.pattern_of(fits.Header({"BAYERPAT": "RGGB", "YBAYROFF": 1})) == "GBRG"
    assert bayer.pattern_of(fits.Header({"BAYERPAT": "RGGB", "XBAYROFF": 1, "YBAYROFF": 1})) == "BGGR"
    assert bayer.pattern_of(fits.Header({"FILTER": "V"})) is None


def test_channel_header_keeps_the_sky_position():
    h = fits.Header({"CTYPE1": "RA---TAN", "CTYPE2": "DEC--TAN", "CRVAL1": 30.0, "CRVAL2": 45.0})
    h.update({"CRPIX1": 101.3, "CRPIX2": 80.7, "CD1_1": -2e-4, "CD1_2": 1e-5, "CD2_1": 1e-5, "CD2_2": 2e-4})
    h.update({"EGAIN": 1.5, "XPIXSZ": 3.76})
    full = WCS(h)
    for colour, (oy, ox) in (("R", (0, 0)), ("B", (1, 1)), ("G", (0.5, 0.5))):
        ch = bayer.channel_header(h, "RGGB", colour)
        j, i = 7.0, 11.0  # 0-based channel pixel -> 0-based mosaic pixel 2 j + offset
        assert np.allclose(WCS(ch).pixel_to_world_values(i, j), full.pixel_to_world_values(2 * i + ox, 2 * j + oy))
        assert ch["FILTER"] == {"R": "TR", "G": "TG", "B": "TB"}[colour] and ch["XPIXSZ"] == 7.52
        assert ch["EGAIN"] == (3.0 if colour == "G" else 1.5)  # the mean of two greens holds twice the electrons
        assert "BAYERPAT" not in ch


def test_mosaic_is_calibrated_then_split(tmp_path):
    """bias + flat * sky on the mosaic; the calibrated channels must equal the true sky of each colour, and a hot
    pixel on a red site is filled from red pixels only."""
    from astrowb.engine.steps import execute

    class Ctx:
        def progress(self, *a):
            pass

        def check(self):
            pass

    rng = np.random.default_rng(4)
    shape = (16, 24)
    sky = {c: np.full(shape, v, np.float32) for c, v in (("R", 300.0), ("G1", 900.0), ("G2", 910.0), ("B", 150.0))}
    truth = mosaic(sky["R"], sky["G1"], sky["G2"], sky["B"])
    flat = rng.uniform(0.8, 1.2, truth.shape).astype(np.float32)
    bias = np.float32(500.0) + rng.normal(0, 0.01, truth.shape).astype(np.float32)
    hot = np.zeros(truth.shape, np.float32)
    hot[4, 6] = 3000.0  # a hot pixel on a red site (even row, even column), in the darks and the light
    raw = tmp_path / "raw"
    for kind in ("bias", "dark", "flat", "light"):
        (raw / kind).mkdir(parents=True)
    common = {"BAYERPAT": "RGGB", "EGAIN": 1.0}
    for i in range(3):
        fits.PrimaryHDU(bias, fits.Header(common | {"IMAGETYP": "Bias", "EXPTIME": 0.0})).writeto(
            raw / f"bias/b{i}.fits"
        )
        d = bias + hot + rng.normal(0, 1, truth.shape).astype(np.float32)
        fits.PrimaryHDU(d, fits.Header(common | {"IMAGETYP": "Dark", "EXPTIME": 10.0})).writeto(raw / f"dark/d{i}.fits")
        f = bias + 20000 * flat
        fits.PrimaryHDU(f, fits.Header(common | {"IMAGETYP": "Flat", "EXPTIME": 1.0})).writeto(raw / f"flat/f{i}.fits")
    hl = fits.Header(common | {"IMAGETYP": "Light", "EXPTIME": 10.0, "DATE-OBS": "2026-11-15T20:00:00"})
    fits.PrimaryHDU(bias + hot + flat * truth, hl).writeto(raw / "light/l.fits")
    frames = execute("calibration.scan", {"folder": str(raw)}, {}, Ctx())["frames"]
    out = execute("calibration.run", {"frames": frames, "output_dir": str(tmp_path / "cal")}, {}, Ctx())
    names = sorted(Path(p).name for p in out["calibrated"])
    assert names == ["l_B.fits", "l_G.fits", "l_R.fits"]
    get = {n[2]: fits.getdata(tmp_path / "cal" / n) for n in names}
    scale = np.median(flat)  # the master flat is normalised to median 1
    assert np.median(get["R"]) == pytest.approx(300.0 * scale, rel=1e-3)
    assert np.median(get["G"]) == pytest.approx(905.0 * scale, rel=1e-3)  # the mean of the two greens
    assert np.median(get["B"]) == pytest.approx(150.0 * scale, rel=1e-3)
    assert fits.getval(tmp_path / "cal" / "l_G.fits", "FILTER") == "TG"
    params = {"fix_defects": True}
    fixed = execute("calibration.run", {"frames": frames, "output_dir": str(tmp_path / "fix")}, params, Ctx())
    r = fits.getdata([p for p in fixed["calibrated"] if p.endswith("_R.fits")][0])
    assert r[2, 3] == pytest.approx(300.0 * scale, rel=0.01)  # filled from red pixels, not from greens (~900)


def write_dng(path, data, when="2026:11:15 21:03:04", exposure=(30, 1)):
    """A minimal uncompressed DNG with an RGGB mosaic (readable by LibRaw)."""
    tags = [
        (50706, "B", 4, (1, 4, 0, 0), True),  # DNGVersion
        (50708, "s", 0, "Test Camera", True),  # UniqueCameraModel
        (33421, "H", 2, (2, 2), True),  # CFARepeatPatternDim
        (33422, "B", 4, (0, 1, 1, 2), True),  # CFAPattern: R G / G B
        (50721, "2i", 9, (10000, 10000, 0, 1, 0, 1, 0, 1, 10000, 10000, 0, 1, 0, 1, 0, 1, 10000, 10000), True),
        (50778, "H", 1, 21, True),  # CalibrationIlluminant1
        (50714, "H", 1, 64, True),  # BlackLevel
        (50717, "H", 1, 4095, True),  # WhiteLevel
        (33434, "2I", 1, exposure, True),  # ExposureTime
        (36867, "s", 0, when, True),  # DateTimeOriginal
        (306, "s", 0, when, True),  # DateTime
    ]
    tifffile.imwrite(path, data, photometric=32803, extratags=tags, metadata=None)


def test_raw_files_become_fits_with_type_and_time(tmp_path):
    from astrowb.calibration.frames import scan

    data = (np.arange(48 * 64).reshape(48, 64) % 4000 + 64).astype(np.uint16)
    for folder in ("Lights", "darks"):
        (tmp_path / folder).mkdir()
        write_dng(tmp_path / folder / "IMG_0001.dng", data)
    written, problems = bayer.convert_raw_folder(tmp_path, clock_utc_offset_h=3.0)
    assert problems == [] and len(written) == 2
    light = tmp_path / "fits_from_raw" / "Lights" / "IMG_0001.fits"
    h = fits.getheader(light)
    assert np.array_equal(fits.getdata(light), data)  # the undeveloped sensor values, untouched
    assert h["BAYERPAT"] == "RGGB" and h["EXPTIME"] == 30.0 and h["SATURATE"] == 4095 and h["BLKLEVEL"] == 64
    assert h["DATE-CAM"] == "2026-11-15T21:03:04" and h["DATE-OBS"] == "2026-11-15T18:03:04"
    kinds = {Path(f.path).parent.name: f.kind for f in scan(tmp_path / "fits_from_raw")[0]}
    assert kinds == {"Lights": "light", "darks": "dark"}
    stamp = light.stat().st_mtime_ns
    assert bayer.convert_raw_folder(tmp_path, clock_utc_offset_h=3.0) == (written, [])  # already converted: kept
    assert light.stat().st_mtime_ns == stamp
    bayer.convert_raw_folder(tmp_path, clock_utc_offset_h=2.0)  # another clock offset: converted again
    assert fits.getval(light, "DATE-OBS") == "2026-11-15T19:03:04"
    (tmp_path / "bad.nef").write_bytes(b"not a raw file")
    assert len(bayer.convert_raw_folder(tmp_path)[1]) == 1  # reported, not fatal


def test_calibrate_page_stacks_each_filter_apart(qtbot, tmp_path):
    from astrowb.ui.workspaces import CalibratePage

    paths = []
    for i, f in enumerate(["TR", "TG", "TB", "TR", "TG", "TB"]):
        p = tmp_path / f"c{i}.fits"
        fits.PrimaryHDU(np.zeros((4, 4), np.float32), fits.Header({"FILTER": f})).writeto(p)
        paths.append(str(p))
    page = CalibratePage()
    qtbot.addWidget(page)
    page.output.setText(str(tmp_path))
    page.calibrated = paths
    got = []
    page.stack_requested.connect(lambda imgs, out, params: got.append((len(imgs), Path(out).name)))
    page._stack()
    assert got == [(2, "stack_TR.fits"), (2, "stack_TG.fits"), (2, "stack_TB.fits")]
    assert page.split_colour.isChecked() and page.clock_offset.value() == 0
