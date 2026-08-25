"""Target pixel files (TESS and Kepler / K2 TPFs, TESScut cut-outs): one table row, with an image, per cadence.
Every good cadence becomes a FITS frame in fits_from_raw/<name>/, so the photometry and every other tool work
on them as on a night of CCD frames.

The archive's TIME is mid-exposure BJD_TDB already (for the spacecraft). A frame carries it as the UTC time at
the geocentre that gives the same BJD_TDB: the application adds the barycentric correction again, for the
geocentre, and gets the archive's time back to well under a millisecond. Cadences flagged as useless
(lightkurve's default quality bitmask) and cadences without a time are left out. Pixel values are e-/s in the
archive; the frames hold electrons (times the exposure), so the photometry's noise is right with GAIN 1.
"""

import re
from pathlib import Path

import numpy as np
from astropy.io import fits

# lightkurve TessQualityFlags.DEFAULT_BITMASK: attitude tweak, safe mode, coarse point, Earth point,
# Argabrightening, desaturation, manual exclude, impulsive outlier, bad calibration (the same bits in Kepler's)
DEFAULT_BITMASK = 1 | 2 | 4 | 8 | 16 | 32 | 128 | 512 | 16384


def is_tpf(path) -> bool:
    try:
        with fits.open(path) as hdul:
            if len(hdul) < 2 or not isinstance(hdul[1], fits.BinTableHDU):
                return False
            cols = hdul[1].columns
            return "TIME" in cols.names and "FLUX" in cols.names and cols["FLUX"].dim is not None
    except (OSError, ValueError):
        return False


def _celestial(hdul):
    """The WCS of the cut-out (the APERTURE image of SPOC TPFs and TESScut files)."""
    from astropy.wcs import WCS

    for hdu in hdul[2:]:
        if isinstance(hdu, fits.ImageHDU):
            w = WCS(hdu.header)
            if w.has_celestial:
                return w.celestial.to_header()
    return fits.Header()


def frames(path) -> list[str]:
    """The FITS frames of a target pixel file (made once, kept while the file is unchanged)."""
    import astropy.units as u
    from astropy.coordinates import EarthLocation, SkyCoord
    from astropy.time import Time

    path = Path(path)
    folder = path.parent / "fits_from_raw" / path.name.split(".fits")[0]
    listing = folder / "frames2.txt"  # written last: an interrupted conversion is done again (2: with PIXNOISE)
    if listing.exists() and listing.stat().st_mtime >= path.stat().st_mtime:
        return [str(folder / n) for n in listing.read_text().split()]
    with fits.open(path) as hdul:
        prim, tab = hdul[0].header, hdul[1].header
        data = hdul[1].data
        t = np.asarray(data["TIME"], float)
        good = np.isfinite(t)
        if "QUALITY" in data.columns.names:
            good &= (np.asarray(data["QUALITY"]) & DEFAULT_BITMASK) == 0
        if not good.any():
            raise ValueError(f"{path.name}: no cadence with a time and good quality")
        flux = np.asarray(data["FLUX"][good], np.float32)
        noise = None
        if "FLUX_ERR" in data.columns.names:  # the archive's noise per pixel: the sky ring of an 11 x 11 px stamp holds
            # the star's wings and its neighbours, and its scatter overstated the errors 3x (WASP-12, TESS sector 20)
            noise = np.nanmedian(np.asarray(data["FLUX_ERR"][good], float).reshape(int(good.sum()), -1), axis=1)
        rows = np.flatnonzero(good)  # names come from the row: TESScut files have CADENCENO 0 on every row
        wcs = _celestial(hdul)
    exptime = float(tab.get("TIMEDEL", 0.0)) * 86400 * float(tab.get("DEADC", 1.0))  # on-source time per cadence
    target = SkyCoord(prim["RA_OBJ"] * u.deg, prim["DEC_OBJ"] * u.deg)
    geocentre = EarthLocation.from_geocentric(0, 0, 0, unit=u.m)
    bjd = Time(t[good] + tab.get("BJDREFI", 0) + tab.get("BJDREFF", 0.0), format="jd", scale="tdb", location=geocentre)
    utc = _utc(bjd, target)
    utc.precision = 6
    stamps = utc.isot
    folder.mkdir(parents=True, exist_ok=True)
    names = []
    for i in range(len(flux)):
        h = fits.Header(wcs)
        h["OBJECT"] = str(prim.get("OBJECT") or prim.get("TICID") or prim.get("KEPLERID") or path.stem)[:60]
        h["TELESCOP"] = str(prim.get("TELESCOP", ""))
        h["RA"], h["DEC"] = target.ra.deg, target.dec.deg
        h["DATE-AVG"] = (stamps[i], "UTC at the geocentre for BJD_TDB")
        h["EXPTIME"] = (exptime, "[s]")
        h["GAIN"] = (1.0, "the pixels are electrons")
        if noise is not None and np.isfinite(noise[i]):
            h["PIXNOISE"] = (float(noise[i] * exptime), "[e-] sky noise per pixel, from the archive's FLUX_ERR")
        h["IMAGETYP"] = "Light Frame"
        h["TPFROW"] = (int(rows[i]), "row of the target pixel file")
        h["TPFSKIP"] = (int(len(t) - len(rows)), "cadences left out (no time or quality flags)")
        h["BJD_TDB"] = (float(bjd[i].jd), "mid-exposure time from the archive")
        name = f"{path.name.split('.fits')[0]}_{int(rows[i]):06d}.fits"
        fits.PrimaryHDU(np.nan_to_num(flux[i] * np.float32(exptime), nan=0.0), h).writeto(folder / name, overwrite=True)
        names.append(name)
    listing.write_text("\n".join(names))
    return [str(folder / n) for n in names]


def _utc(bjd, target):
    """The UTC at the geocentre whose barycentric time is bjd (BJD = t + light travel time(t): two steps converge to
    nanoseconds)."""
    utc = bjd
    for _ in range(2):
        utc = bjd - utc.light_travel_time(target, kind="barycentric", ephemeris="builtin")
    return utc.utc


_ROW = re.compile(r"_(\d{6})\.fits$")


def source(paths):
    """(pixel file, its rows) when every path is a frame frames() made from one target pixel file, else None: the
    photometry then reads the cadences from the file at once instead of 18 758 frames one by one."""
    paths = [Path(p) for p in paths]
    if not paths or len({p.parent for p in paths}) != 1:
        return None
    folder = paths[0].parent
    if folder.parent.name != "fits_from_raw":
        return None
    rows = []
    for p in paths:
        m = _ROW.search(p.name)
        if not m or p.name[: m.start()] != folder.name:
            return None
        rows.append(int(m.group(1)))
    for f in sorted(folder.parent.parent.glob(folder.name + ".fits*")):
        if f.name.split(".fits")[0] == folder.name and is_tpf(f):
            return f, rows
    return None


def cube(path, rows, pixels=True):
    """The cadences of rows as the frames hold them: (electrons (n, ny, nx) float32, sky noise per pixel (n) or None,
    BJD_TDB (n), UTC Time, exposure in s); pixels=False: the times only (no pixels read, None in their place)."""
    import astropy.units as u
    from astropy.coordinates import EarthLocation, SkyCoord
    from astropy.time import Time

    rows = np.asarray(rows, int)
    with fits.open(path) as hdul:
        prim, tab, data = hdul[0].header, hdul[1].header, hdul[1].data
        exptime = float(tab.get("TIMEDEL", 0.0)) * 86400 * float(tab.get("DEADC", 1.0))
        flux = noise = None
        if pixels:
            flux = np.nan_to_num(np.asarray(data["FLUX"][rows], np.float32) * np.float32(exptime), nan=0.0)
        if pixels and "FLUX_ERR" in data.columns.names:
            noise = np.nanmedian(np.asarray(data["FLUX_ERR"][rows], float).reshape(len(rows), -1), axis=1) * exptime
        t = np.asarray(data["TIME"][rows], float) + tab.get("BJDREFI", 0) + tab.get("BJDREFF", 0.0)
    target = SkyCoord(prim["RA_OBJ"] * u.deg, prim["DEC_OBJ"] * u.deg)
    geocentre = EarthLocation.from_geocentric(0, 0, 0, unit=u.m)
    return flux, noise, t, _utc(Time(t, format="jd", scale="tdb", location=geocentre), target), exptime
