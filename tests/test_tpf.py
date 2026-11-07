"""Target pixel files (TESS / Kepler TPFs, TESScut cut-outs) as frames, and timing every eclipse of a long series:
a real TESScut file of AI Dra (sector 24) gave P = 1.19880 d from 42 minima, the literature value."""

from pathlib import Path

import numpy as np
import pytest
from astropy.io import fits

from astrowb import timing
from astrowb.engine.steps import execute
from astrowb.io import bayer, tpf
from astrowb.photometry.lightcurve import target_coord

P, T0 = 1.1988, 2458956.5749  # an Algol-type binary: primary 40 % deep, secondary 8 %


def flux(t):
    ph = ((t - T0) / P + 0.5) % 1 - 0.5
    return 1 - 0.4 * np.exp(-0.5 * (ph / 0.03) ** 2) - 0.08 * np.exp(-0.5 * ((np.abs(ph) - 0.5) / 0.03) ** 2)


def write_tpf(path, n=600, rows=21):
    """A TESScut-like file: TIME in BTJD, FLUX in e-/s, QUALITY, CADENCENO 0 on every row (as TESScut writes)."""
    t = 1955.80 + np.arange(n) / 48  # 30-minute cadence, 12.5 days
    yy, xx = np.mgrid[:rows, :rows]
    star = np.exp(-((xx - 10) ** 2 + (yy - 10) ** 2) / 2.0)
    cube = (5000 * flux(t + 2457000)[:, None, None] * star + 20).astype(np.float32)
    quality = np.zeros(n, np.int32)
    quality[5] = 32  # a desaturation event: left out
    cols = [
        fits.Column("TIME", "D", array=t),
        fits.Column("CADENCENO", "J", array=np.zeros(n, np.int32)),
        fits.Column("FLUX", f"{rows * rows}E", dim=f"({rows},{rows})", array=cube),
        fits.Column("QUALITY", "J", array=quality),
    ]
    table = fits.BinTableHDU.from_columns(cols, name="PIXELS")
    table.header.update({"BJDREFI": 2457000, "BJDREFF": 0.0, "TIMEDEL": 1 / 48, "DEADC": 0.792})
    aperture = fits.ImageHDU(np.ones((rows, rows), np.int32), name="APERTURE")
    aperture.header.update(
        {"CTYPE1": "RA---TAN", "CTYPE2": "DEC--TAN", "CRVAL1": 254.0758, "CRVAL2": 52.6983, "CRPIX1": 11, "CRPIX2": 11}
        | {"CDELT1": -0.0058, "CDELT2": 0.0058}
    )
    primary = fits.PrimaryHDU(header=fits.Header({"TELESCOP": "TESS", "RA_OBJ": 254.0758, "DEC_OBJ": 52.6983}))
    fits.HDUList([primary, table, aperture]).writeto(path)
    return t + 2457000


def test_a_target_pixel_file_becomes_frames_with_the_archive_times(tmp_path):
    path = tmp_path / "tess-s0024-2-1_cut_astrocut.fits"
    bjd = write_tpf(path)
    assert tpf.is_tpf(path) and not tpf.is_tpf(tmp_path / "nothing.fits")
    frames = bayer.fits_paths([str(path)])
    assert len(frames) == len(bjd) - 1 and len(set(frames)) == len(frames)  # one per good cadence, distinct names
    tpf.finish(path)  # the frames after the first are written in the background
    h = fits.getheader(frames[10])
    back = timing.bjd_tdb(timing.mid_time(h), target_coord(h)).jd
    assert abs(back - bjd[11]) * 86400 < 0.001  # the application's BJD_TDB is the archive's
    assert h["EXPTIME"] == pytest.approx(1800 * 0.792) and h["CTYPE1"] == "RA---TAN"
    assert h["TPFSKIP"] == 1  # the flagged cadence, told to the user on the Photometry page
    with fits.open(frames[10]) as f:  # written card by card (fast), still a valid FITS file
        f.verify("exception")
        with fits.open(path) as src:
            expect = src[1].data["FLUX"][11] * np.float32(1800 * 0.792)
        assert np.array_equal(f[0].data, expect) and f[0].header["TPFROW"] == 11 and f[0].header["BITPIX"] == -32
    assert str(bayer.fits_copy(path)) == frames[0]  # opened as one image: its first good cadence


def test_space_photometry_without_comparison_stars_and_every_minimum(tmp_path):
    path = tmp_path / "cut.fits"
    write_tpf(path)
    frames = bayer.fits_paths([str(path)])

    class Ctx:
        def progress(self, *a):
            pass

        def check(self):
            pass

    lc = execute("photometry.light_curve", {"images": frames, "target_xy": [10, 10], "comps_xy": []}, {}, Ctx())
    lc = lc["light_curve"]
    assert lc["time_scale"] == "BJD_TDB" and 0.35 < 1 - min(lc["rel_flux"]) / np.median(lc["rel_flux"]) < 0.45
    with pytest.raises(ValueError, match="shows 1[01] eclipses: give T0 and the period"):
        execute("timeseries.minimum", {"light_curve": lc}, {"method": "kvw"}, Ctx())
    out = execute("timeseries.minimum", {"light_curve": lc}, {"method": "kvw", "t0": T0, "period": P}, Ctx())
    minima = out["minimum"]["minima"]
    primaries = [m for m in minima if m["kind"] == "I"]
    assert len(primaries) >= 9 and any(m["kind"] == "II" and m["epoch"] % 1 == 0.5 for m in minima)
    assert max(abs(m["o_minus_c"]) for m in minima) * 1440 < 3  # minutes


def test_errors_of_a_small_stamp_come_from_the_archive_noise(tmp_path):
    """11 x 11 px with a neighbour in the sky ring (WASP-12, TESS sector 20): the ring's scatter is the neighbour and
    the wings, not noise, and made the errors 3x too large; FLUX_ERR gives the noise per pixel."""
    n, rows, sigma = 300, 11, 15.0
    rng = np.random.default_rng(4)
    yy, xx = np.mgrid[:rows, :rows]
    r2 = (xx - 5) ** 2 + (yy - 5) ** 2  # an undersampled core with wide wings, as TESS has
    star = 3e4 * np.exp(-r2 / 1.6) + 800 * np.exp(-r2 / 12) + 900 * np.exp(-((xx - 9) ** 2 + (yy - 1) ** 2) / 1.6)
    cube = (star[None] + rng.normal(0, sigma, (n, rows, rows))).astype(np.float32)
    cols = [
        fits.Column("TIME", "D", array=1900.0 + np.arange(n) / 720),
        fits.Column("FLUX", f"{rows * rows}E", dim=f"({rows},{rows})", array=cube),
        fits.Column("FLUX_ERR", f"{rows * rows}E", dim=f"({rows},{rows})", array=np.full_like(cube, sigma)),
        fits.Column("QUALITY", "J", array=np.zeros(n, np.int32)),
    ]
    table = fits.BinTableHDU.from_columns(cols, name="PIXELS")
    table.header.update({"BJDREFI": 2457000, "BJDREFF": 0.0, "TIMEDEL": 1 / 720, "DEADC": 0.792})
    wcs = {"CTYPE1": "RA---TAN", "CTYPE2": "DEC--TAN", "CRVAL1": 97.6, "CRVAL2": 29.7, "CRPIX1": 6, "CRPIX2": 6}
    aperture = fits.ImageHDU(np.ones((rows, rows), np.int32), name="APERTURE")
    aperture.header.update(wcs | {"CDELT1": -0.0058, "CDELT2": 0.0058})
    primary = fits.PrimaryHDU(header=fits.Header({"TELESCOP": "TESS", "RA_OBJ": 97.6, "DEC_OBJ": 29.7}))
    path = tmp_path / "small_tp.fits"
    fits.HDUList([primary, table, aperture]).writeto(path)
    frames = bayer.fits_paths([str(path)])
    assert fits.getval(frames[0], "PIXNOISE") == pytest.approx(sigma * 120 * 0.792, rel=1e-3)

    class Ctx:
        def progress(self, *a):
            pass

        def check(self):
            pass

    params = {"r_ap": 2.0, "r_in": 4.0, "r_out": 6.0}
    lc = execute("photometry.light_curve", {"images": frames, "target_xy": [5, 5], "comps_xy": []}, params, Ctx())
    lc = lc["light_curve"]
    scatter, err = np.std(lc["rel_flux"]), np.median(lc["rel_flux_err"])
    assert 0.7 < err / scatter < 1.4
    # the page's default rings (4, 10, 16 px) do not fit 11 x 11 px: chosen from the stars instead of NaN everywhere
    lc = execute("photometry.light_curve", {"images": frames[:20], "target_xy": [5, 5], "comps_xy": []}, {}, Ctx())
    lc = lc["light_curve"]
    assert lc["apertures"]["replaced"] and np.all(np.isfinite(lc["rel_flux"])) and lc["apertures"]["r_out"] <= 7


def test_the_cadences_of_a_pixel_file_are_measured_at_once_as_frame_by_frame(tmp_path):
    """measure_cube on a cube = measure() on each frame (fluxes, errors, sky); a pixel file's frames take that path
    (real TESS file: 224 s -> 8 s) and are ordered from the file's rows without opening every header."""
    from astrowb import timing
    from astrowb.photometry.aperture import measure, measure_cube

    rng = np.random.default_rng(2)
    yy, xx = np.mgrid[:13, :15]
    star = 4000 * np.exp(-((xx - 7.3) ** 2 + (yy - 6.2) ** 2) / 2.2)
    star += 300 * np.exp(-((xx - 12) ** 2 + (yy - 2) ** 2) / 2)
    cube = (star[None] * rng.uniform(0.95, 1.05, (40, 1, 1)) + rng.normal(20, 5, (40, 13, 15))).astype(np.float32)
    xy = np.array([[7.3, 6.2], [12.0, 2.0]])
    noise = rng.uniform(4, 6, 40)
    f, e, s, _ = measure_cube(cube, xy, 2.5, 4.0, 6.0, 1.0, noise)
    for i in (0, 17, 39):
        f1, e1, s1 = measure(cube[i], xy, 2.5, 4.0, 6.0, 1.0, noise[i])
        assert np.allclose(f[i], f1, rtol=1e-9) and np.allclose(e[i], e1, rtol=1e-9) and np.allclose(s[i], s1)
    path = tmp_path / "cut_tp.fits"
    write_tpf(path)
    frames = bayer.fits_paths([str(path)])
    assert tpf.source(frames) is not None and tpf.source([str(path)]) is None
    shuffled = frames[::-1]
    times = {}
    assert timing.chronological(shuffled, times) == frames and len(times) == len(frames)


def test_a_frame_asked_for_before_the_background_writer_is_written_on_the_spot(tmp_path):
    """Opening a pixel file returns the frame names and the first frame at once; a frame read before the
    background writer got to it (here: deleted) is written when it is opened, with the same pixels and times."""
    from astrowb.calibration.masters import load
    from astrowb.io.lzw import readable

    path = tmp_path / "tess-s0024-2-1_cut_astrocut.fits"
    write_tpf(path)
    frames = tpf.frames(path)
    tpf.finish(path)
    before = (
        fits.getheader(frames[40]),
        fits.getdata(frames[40], memmap=False),
    )  # Windows: a mapped file cannot be deleted
    for f in frames[30:50]:
        Path(f).unlink()
    data, h = load(frames[40])  # through readable(): written now
    assert np.array_equal(data, before[1]) and h["TPFROW"] == before[0]["TPFROW"]
    assert h["BJD_TDB"] == before[0]["BJD_TDB"] and abs(timing.mid_time(h) - timing.mid_time(before[0])).sec < 1e-4
    assert readable(tmp_path / "other.fits") == tmp_path / "other.fits"  # any other missing file: left alone
    assert tpf.frames(path) == frames  # opened again: the listing, and the missing frames written again
    tpf.finish(path)
    assert all(Path(f).exists() for f in frames)
