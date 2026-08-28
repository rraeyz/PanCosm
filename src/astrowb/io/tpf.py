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
from concurrent.futures import ThreadPoolExecutor
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
    """The FITS frames of a target pixel file (kept while the file is unchanged). The names and the first frame
    are there at once; the other frames are written by a background thread, and any frame asked for before it gets
    there is written on the spot (io.lzw.readable): creating 17 000 files took 3 of the 7 s of opening one, longer
    than lightkurve needs to measure the whole light curve (4 s)."""
    path = Path(path)
    folder = _folder(path)
    listing = folder / "frames2.txt"
    if listing.exists() and listing.stat().st_mtime >= path.stat().st_mtime:
        names = listing.read_text().split()
        if not (folder / names[0]).exists():
            _write(path, [0])
        _start_writer(path)  # frames a deleted or interrupted conversion left out
        return [str(folder / n) for n in names]
    rows = _good_rows(path)
    names = [_name(path, r) for r in rows]
    folder.mkdir(parents=True, exist_ok=True)
    _write(path, [0])
    tmp = listing.with_suffix(".part")
    tmp.write_text("\n".join(names))
    tmp.replace(listing)
    _start_writer(path)
    return [str(folder / n) for n in names]


def _folder(path):
    return Path(path).parent / "fits_from_raw" / Path(path).name.split(".fits")[0]


def _name(path, row):
    return f"{Path(path).name.split('.fits')[0]}_{int(row):06d}.fits"


def _good_rows(path):
    """Rows of the cadences that become frames: a time and no flag of lightkurve's default quality bitmask."""
    with fits.open(path) as hdul:
        data = hdul[1].data
        t = np.asarray(data["TIME"], float)
        good = np.isfinite(t)
        if "QUALITY" in data.columns.names:
            good &= (np.asarray(data["QUALITY"]) & DEFAULT_BITMASK) == 0
    if not good.any():
        raise ValueError(f"{Path(path).name}: no cadence with a time and good quality")
    return np.flatnonzero(good)  # names come from the row: TESScut files have CADENCENO 0 on every row


_writers = {}  # pixel file -> background writing thread


def _start_writer(path):
    import threading

    key = str(Path(path).resolve())
    if key in _writers and _writers[key].is_alive():
        return
    _writers[key] = threading.Thread(target=_write, args=(path, None), daemon=True, name="tpf frames")
    _writers[key].start()


def finish(path=None):
    """Wait until the background writing of a pixel file's frames (or of every one) is done."""
    for key, th in list(_writers.items()):
        if path is None or key == str(Path(path).resolve()):
            th.join()


def materialize(frame):
    """Write a frame of a pixel file that is asked for before the background writer got to it. True when frame is
    such a frame (now written), False for any other path."""
    frame = Path(frame)
    m = _ROW.search(frame.name)
    if not m or frame.parent.parent.name != "fits_from_raw" or frame.name[: m.start()] != frame.parent.name:
        return False
    for f in sorted(frame.parent.parent.parent.glob(frame.parent.name + ".fits*")):
        if f.name.split(".fits")[0] == frame.parent.name and is_tpf(f):
            index = np.flatnonzero(_good_rows(f) == int(m.group(1)))
            if len(index):
                _write(f, [int(index[0])])
                return frame.exists()
    return False


def _put(target, data):
    """Write a frame once, atomically (a reader never sees half a file); a frame already there is left as it is
    (on Windows it may be open)."""
    import os
    import threading

    if target.exists():
        return
    tmp = target.with_name(f"{target.name}.{os.getpid()}.{threading.get_ident()}.part")
    tmp.write_bytes(data)
    try:
        tmp.replace(target)
    except OSError:  # written meanwhile by another writer and open: that copy is the same frame
        tmp.unlink(missing_ok=True)


def _write(path, which=None):
    """Write the frames of the good cadences `which` (indices among them; None: every one not written yet)."""
    import astropy.units as u
    from astropy.coordinates import EarthLocation, SkyCoord
    from astropy.time import Time

    path = Path(path)
    folder = _folder(path)
    folder.mkdir(parents=True, exist_ok=True)
    with fits.open(path) as hdul:
        prim, tab = hdul[0].header, hdul[1].header
        data = hdul[1].data
        t_all = np.asarray(data["TIME"], float)
        good = _good_rows(path)
        n_skip = len(t_all) - len(good)
        if which is None:
            which = [i for i, r in enumerate(good) if not (folder / _name(path, r)).exists()]
            if not which:
                return
        rows = good[np.asarray(which, int)]
        flux = np.asarray(data["FLUX"][rows], np.float32)
        noise = None
        if "FLUX_ERR" in data.columns.names:  # the archive's noise per pixel: the sky ring of an 11 x 11 px stamp holds
            # the star's wings and its neighbours, and its scatter overstated the errors 3x (WASP-12, TESS sector 20)
            noise = np.nanmedian(np.asarray(data["FLUX_ERR"][rows], float).reshape(len(rows), -1), axis=1)
        t = t_all[rows]
        wcs = _celestial(hdul)
    exptime = float(tab.get("TIMEDEL", 0.0)) * 86400 * float(tab.get("DEADC", 1.0))  # on-source time per cadence
    target = SkyCoord(prim["RA_OBJ"] * u.deg, prim["DEC_OBJ"] * u.deg)
    geocentre = EarthLocation.from_geocentric(0, 0, 0, unit=u.m)
    bjd = Time(t + tab.get("BJDREFI", 0) + tab.get("BJDREFF", 0.0), format="jd", scale="tdb", location=geocentre)
    utc = _utc(bjd, target)
    utc.precision = 6
    stamps = np.atleast_1d(utc.isot)
    h = fits.Header(wcs)
    h["OBJECT"] = str(prim.get("OBJECT") or prim.get("TICID") or prim.get("KEPLERID") or path.stem)[:60]
    h["TELESCOP"] = str(prim.get("TELESCOP", ""))
    h["RA"], h["DEC"] = target.ra.deg, target.dec.deg
    h["DATE-AVG"] = (stamps[0], "UTC at the geocentre for BJD_TDB")
    h["EXPTIME"] = (exptime, "[s]")
    h["GAIN"] = (1.0, "the pixels are electrons")
    if noise is not None:
        h["PIXNOISE"] = (0.0, NOISE_COMMENT)
    h["IMAGETYP"] = "Light Frame"
    h["TPFROW"] = (0, "row of the target pixel file")
    h["TPFSKIP"] = (int(n_skip), "cadences left out (no time or quality flags)")
    h["BJD_TDB"] = (0.0, "mid-exposure time from the archive")
    writer = _FrameWriter(fits.PrimaryHDU(flux[0], h).header)
    bjd_jd = np.atleast_1d(bjd.jd)
    pixels = np.nan_to_num(flux * np.float32(exptime), nan=0.0)
    # creating 17 000 small files is most of the time (the file system, not Python): a few at once
    with ThreadPoolExecutor(8) as pool:
        for start in range(0, len(rows), 1000):  # in blocks, so the bytes waiting to be written stay small
            files = []
            for i in range(start, min(start + 1000, len(rows))):
                cards = {"DATE-AVG": (stamps[i], "UTC at the geocentre for BJD_TDB"),
                         "TPFROW": (int(rows[i]), "row of the target pixel file"),
                         "BJD_TDB": (float(bjd_jd[i]), "mid-exposure time from the archive")}  # fmt: skip
                if noise is not None:
                    cards["PIXNOISE"] = (float(noise[i] * exptime), NOISE_COMMENT) if np.isfinite(noise[i]) else None
                files.append((folder / _name(path, rows[i]), writer.encode(pixels[i], cards)))
            list(pool.map(lambda f: _put(*f), files))


NOISE_COMMENT = "[e-] sky noise per pixel, from the archive's FLUX_ERR"


class _FrameWriter:
    """Writes many single-image FITS files that differ only in a few header cards and the pixels: the header is made
    once and only those cards are formatted again (astropy rebuilt and verified the whole header for each of 17 000
    TESS cadences: 43 s of opening a pixel file)."""

    def __init__(self, header):
        self.cards = [c.image for c in header.cards]
        self.index = {k: i for i, k in enumerate(header.keys())}
        self.dtype = np.dtype(">f4")
        self.templates = {}  # (key, comment) -> astropy's card for the first value, "" if ours differed from it

    def card(self, key, value, comment):
        """fits.Card(key, value, comment).image with only its value field (from column 11) formatted per frame
        (astropy's Card took 6 of the 11 s of writing 16 942 TESS frames). The first value of each card is checked
        against astropy's card; a card that differed, or a value of another width, is left to astropy."""
        field = _field(value)
        template = self.templates.get((key, comment))
        if template is None:
            image = fits.Card(key, value, comment).image
            ok = field is not None and image[:10] + field + image[10 + len(field) :] == image
            self.templates[(key, comment)] = (image, len(field)) if ok else ("", -1)
            return image
        image, width = template
        if field is not None and len(field) == width:
            return image[:10] + field + image[10 + width :]
        return fits.Card(key, value, comment).image

    def encode(self, image, cards):
        """The bytes of one FITS file: the header with these cards replaced, then the pixels."""
        lines = list(self.cards)
        for key, value in cards.items():
            lines[self.index[key]] = " " * 80 if value is None else self.card(key, *value)
        text = "".join(lines) + "END".ljust(80)
        head = text.encode("ascii").ljust(-(-len(text) // 2880) * 2880, b" ")
        data = np.ascontiguousarray(image, self.dtype).tobytes()
        return head + data + b"\0" * (-len(data) % 2880)


def _field(value):
    """The fixed-format FITS value field (from column 11) of a string, integer or float; None for other values."""
    if isinstance(value, str):
        return ("'" + f"{value.replace(chr(39), chr(39) * 2):8}" + "'").ljust(20)
    if isinstance(value, (bool, np.bool_)) or not np.isfinite(value):
        return None
    field = str(int(value)) if isinstance(value, (int, np.integer)) else repr(float(value)).upper()
    return field.rjust(20) if len(field) <= 20 else None


def _utc(bjd, target, nodes=1000):
    """The UTC at the geocentre whose barycentric time is bjd (BJD = t + light travel time(t): two steps converge to
    nanoseconds). For many times the light travel time is computed exactly at `nodes` of them and interpolated
    between (it changes by at most ~0.01 s per day: under 1e-5 s off over a TESS sector; astropy's transformation for
    each of 16 942 cadences took 6.5 s, twice per pixel file)."""
    from astropy.time import TimeDelta

    jd = bjd.jd
    if len(jd) > 2 * nodes:
        gap = np.flatnonzero(np.diff(jd) > 10 * np.median(np.diff(jd)))  # both sides of a data gap are nodes too:
        # a straight line over the 1.5-day mid-sector gap was 2.7 ms off
        at = np.unique(np.r_[np.linspace(0, len(jd) - 1, nodes).round().astype(int), gap, gap + 1])
        exact = _utc(bjd[at], target, nodes)
        corr = np.interp(jd, jd[at], (bjd[at] - exact.tdb).jd)  # days, BJD - geocentric TDB
        return (bjd - TimeDelta(corr, format="jd")).utc
    utc = bjd
    for _ in range(2):
        utc = bjd - _light_travel_time(utc, target)
    return utc.utc


def _light_travel_time(t, target):
    """Time.light_travel_time(target, "barycentric", "builtin") for an observer at the geocentre: the Earth's
    barycentric position along the direction of the target, over c. Astropy also places the observer, which read
    the IERS polar-motion table (1.3 s) to rotate a zero vector."""
    import astropy.constants as const
    from astropy.coordinates import UnitSphericalRepresentation, get_body_barycentric
    from astropy.time import TimeDelta

    earth = get_body_barycentric("earth", t.tdb, ephemeris="builtin")
    sky = target.icrs.represent_as(UnitSphericalRepresentation).to_cartesian()
    return TimeDelta(earth.dot(sky) / const.c, scale="tdb")


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
