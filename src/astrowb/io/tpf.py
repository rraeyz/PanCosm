"""Target pixel files (TESS and Kepler / K2 TPFs, TESScut cut-outs): one table row, with an image, per cadence.
Every good cadence becomes a FITS frame in fits_from_raw/<name>/, so the photometry and every other tool work
on them as on a night of CCD frames.

The archive's TIME is mid-exposure BJD_TDB already (for the spacecraft). A frame carries it as the UTC time at
the geocentre that gives the same BJD_TDB: the application adds the barycentric correction again, for the
geocentre, and gets the archive's time back to well under a millisecond. Cadences flagged as useless
(lightkurve's default quality bitmask) and cadences without a time are left out. Pixel values are e-/s in the
archive; the frames hold electrons (times the exposure), so the photometry's noise is right with GAIN 1.
"""

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
    listing = folder / "frames.txt"  # written last: an interrupted conversion is done again
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
        rows = np.flatnonzero(good)  # names come from the row: TESScut files have CADENCENO 0 on every row
        wcs = _celestial(hdul)
    exptime = float(tab.get("TIMEDEL", 0.0)) * 86400 * float(tab.get("DEADC", 1.0))  # on-source time per cadence
    target = SkyCoord(prim["RA_OBJ"] * u.deg, prim["DEC_OBJ"] * u.deg)
    geocentre = EarthLocation.from_geocentric(0, 0, 0, unit=u.m)
    bjd = Time(t[good] + tab.get("BJDREFI", 0) + tab.get("BJDREFF", 0.0), format="jd", scale="tdb", location=geocentre)
    utc = bjd
    for _ in range(2):  # BJD = t + light travel time(t): two steps converge to nanoseconds
        utc = bjd - utc.light_travel_time(target, kind="barycentric", ephemeris="builtin")
    utc = utc.utc
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
        h["IMAGETYP"] = "Light Frame"
        h["TPFROW"] = (int(rows[i]), "row of the target pixel file")
        h["BJD_TDB"] = (float(bjd[i].jd), "mid-exposure time from the archive")
        name = f"{path.name.split('.fits')[0]}_{int(rows[i]):06d}.fits"
        fits.PrimaryHDU(np.nan_to_num(flux[i] * np.float32(exptime), nan=0.0), h).writeto(folder / name, overwrite=True)
        names.append(name)
    listing.write_text("\n".join(names))
    return [str(folder / n) for n in names]
