"""Target pixel files (TESS / Kepler TPFs, TESScut cut-outs) as frames, and timing every eclipse of a long series:
a real TESScut file of AI Dra (sector 24) gave P = 1.19880 d from 42 minima, the literature value."""

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
    h = fits.getheader(frames[10])
    back = timing.bjd_tdb(timing.mid_time(h), target_coord(h)).jd
    assert abs(back - bjd[11]) * 86400 < 0.001  # the application's BJD_TDB is the archive's
    assert h["EXPTIME"] == pytest.approx(1800 * 0.792) and h["CTYPE1"] == "RA---TAN"
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
