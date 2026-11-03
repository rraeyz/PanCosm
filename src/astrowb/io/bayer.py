"""Colour (one-shot-colour, Bayer) cameras and DSLR / mirrorless raw files.

Scientific use of a colour sensor (e.g. the AAVSO DSLR Observing Manual): calibrate the raw mosaic (bias, dark,
flat are subtracted / divided pixel by pixel, so the mosaic is kept), then extract each colour as its own
half-size image without interpolation — one "superpixel" per 2 x 2 cell: R, the mean of the two greens, B.
Interpolating debayer methods mix neighbouring pixels and change the star profiles; they are for pictures only.
The green channel is closest to Johnson V (AAVSO filter code TG), red to R (TR), blue to B (TB).

Raw files are read with LibRaw (through rawpy) as the undeveloped sensor values: no white balance, no gamma,
no black-level subtraction (the bias frames remove it), no interpolation.
"""

from datetime import timedelta
from pathlib import Path

import numpy as np
from astropy.io import fits

from ..hdr import get

PATTERNS = ("RGGB", "BGGR", "GRBG", "GBRG")
RAW_SUFFIXES = (".cr2", ".cr3", ".crw", ".nef", ".nrw", ".arw", ".srf", ".sr2", ".dng", ".orf", ".rw2", ".raf",
                ".pef", ".srw", ".erf", ".3fr", ".iiq", ".mrw", ".x3f", ".raw")  # fmt: skip
FILTER_CODE = {"R": "TR", "G": "TG", "B": "TB"}  # AAVSO codes for DSLR / colour-camera channels
# ordinary pictures: phones, compact cameras, programs that save JPEG / PNG / TIFF
PICTURE_SUFFIXES = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp")
FITS_SUFFIXES = (".fits", ".fit", ".fts", ".fits.gz", ".fit.gz", ".fts.gz", ".fits.fz")
# for file dialogs: everything the application can open as an image
OPEN_PATTERNS = " ".join(f"*{s} *{s.upper()}" for s in FITS_SUFFIXES + RAW_SUFFIXES + PICTURE_SUFFIXES)


def pattern_of(header):
    """The 2 x 2 colour pattern at the first stored pixel (row 0, column 0), or None for a monochrome frame.
    BAYERPAT (N.I.N.A., SharpCap, ASIAIR, MaxIm "BAYERPAT"/"COLORTYP") shifted by XBAYROFF / YBAYROFF."""
    pat = str(header.get("BAYERPAT", header.get("COLORTYP", "")) or "").strip().upper()
    if pat not in PATTERNS:
        return None
    cell = np.array(list(pat)).reshape(2, 2)
    dx, dy = int(get(header, "XBAYROFF", default=0)) % 2, int(get(header, "YBAYROFF", default=0)) % 2
    return "".join(np.roll(cell, (-dy, -dx), axis=(0, 1)).ravel())


def _phases(pattern):
    """{colour: [(row offset, column offset), ...]} inside the 2 x 2 cell."""
    out = {}
    for k, c in enumerate(pattern):
        out.setdefault(c, []).append(divmod(k, 2))
    return out


def split(image, pattern):
    """Superpixel extraction: {"R", "G", "B": half-size float32 images}; G is the mean of the two greens.
    An odd last row / column (an incomplete cell) is dropped."""
    a = np.asarray(image, np.float32)
    h, w = a.shape[0] // 2 * 2, a.shape[1] // 2 * 2
    out = {}
    for c, offs in _phases(pattern).items():
        planes = [a[dy:h:2, dx:w:2] for dy, dx in offs]
        out[c] = planes[0] if len(planes) == 1 else (planes[0] + planes[1]) * np.float32(0.5)
    return out


def repair_cfa(image, bad, repair):
    """Run a defect repair on each colour of the mosaic separately, so a bad pixel is filled from pixels of its
    own colour only."""
    out = np.asarray(image, np.float32).copy()
    for dy in (0, 1):
        for dx in (0, 1):
            out[dy::2, dx::2] = repair(out[dy::2, dx::2], bad[dy::2, dx::2])
    return out


def channel_header(header, pattern, colour):
    """Header of one extracted channel: FILTER code, pixel size and gain of the superpixel, WCS moved to the
    half-size grid at the true position of that colour's pixels in the cell."""
    h = header.copy()
    for k in ("BAYERPAT", "COLORTYP", "XBAYROFF", "YBAYROFF"):
        h.remove(k, ignore_missing=True)
    offs = _phases(pattern)[colour]
    n = len(offs)
    oy, ox = np.mean([o[0] for o in offs]), np.mean([o[1] for o in offs])
    h["CFACHAN"] = (colour, f"colour channel of a {pattern} sensor (superpixel)")
    h["FILTER"] = (FILTER_CODE[colour], "AAVSO code of the colour-camera channel")
    for k in ("XPIXSZ", "YPIXSZ", "PIXSIZE1", "PIXSIZE2"):
        if get(h, k) is not None:
            h[k] = get(h, k) * 2
    if n == 2:  # the mean of two pixels: twice the electrons per ADU, read noise / sqrt(2)
        if "EGAIN" in h:
            h["EGAIN"] = (get(h, "EGAIN", default=1.0) * 2, "e-/ADU of the mean of the two green pixels")
        if "RDNOISE" in h:
            h["RDNOISE"] = get(h, "RDNOISE", default=0.0) / np.sqrt(2)
    # pixel j (1-based) of the channel sits at 1-based mosaic coordinate 2 j - 1 + offset
    for axis, off in ((1, ox), (2, oy)):
        if f"CRPIX{axis}" in h:
            h[f"CRPIX{axis}"] = (float(h[f"CRPIX{axis}"]) + 1 - off) / 2
    for k in ("CD1_1", "CD1_2", "CD2_1", "CD2_2", "CDELT1", "CDELT2"):
        if k in h:
            h[k] = float(h[k]) * 2
    h.add_history(f"{colour} channel extracted from the {pattern} mosaic (2 x 2 superpixel, no interpolation)")
    return h


def _kind_from_path(path, root):
    """IMAGETYP from the folder names between root and the file (e.g. raw/darks/IMG_0001.CR2 -> Dark)."""
    from ..calibration.frames import _PATTERNS

    for part in reversed(Path(path).relative_to(root).parts[:-1]):
        for kind, pattern in _PATTERNS:
            if pattern.search(part):
                return kind.capitalize()
    return None


def read_raw(path, clock_utc_offset_h=0.0):
    """(mosaic as uint16, FITS header) of a camera raw file. DATE-OBS is the camera clock (start of the exposure,
    1 s resolution) minus clock_utc_offset_h hours; the original clock reading is kept in DATE-CAM."""
    import rawpy

    with rawpy.imread(str(path)) as raw:
        colours = raw.raw_colors_visible
        desc = raw.color_desc.decode()
        cell = colours[:2, :2]
        pattern = "".join(desc[i] for i in cell.ravel())
        if raw.num_colors != 3 or pattern not in PATTERNS or not (np.tile(cell, (3, 3)) == colours[:6, :6]).all():
            raise ValueError(f"{Path(path).name}: not a 2 x 2 Bayer sensor (e.g. Fujifilm X-Trans, Foveon)")
        data = np.array(raw.raw_image_visible, dtype=np.uint16)
        other, black, white = raw.other, raw.black_level_per_channel, raw.white_level
    h = fits.Header()
    h["BAYERPAT"] = (pattern, "colour pattern at the first pixel")
    h["EXPTIME"] = (float(other.shutter_speed), "[s] from the raw file")
    if other.iso_speed:
        h["ISOSPEED"] = (float(other.iso_speed), "ISO setting")
    h["BLKLEVEL"] = (float(np.mean(black)), "camera black level (ADU), removed by the bias")
    h["SATURATE"] = (float(white), "[ADU] sensor white level")
    stamp = other.timestamp
    if stamp:
        h["DATE-CAM"] = (stamp.isoformat(timespec="seconds"), "camera clock at the start of the exposure")
        utc = stamp - timedelta(hours=float(clock_utc_offset_h))
        h["DATE-OBS"] = (utc.isoformat(timespec="seconds"), f"UTC = camera clock - {clock_utc_offset_h:g} h")
    h["CLKOFFS"] = (float(clock_utc_offset_h), "[h] camera clock minus UTC, given by the user")
    h["RAWFILE"] = (Path(path).name, "camera raw file")
    return data, h


_EXIF_IFD, _DATE_ORIGINAL, _EXPOSURE, _ISO, _MODEL, _FOCAL = 0x8769, 36867, 33434, 34855, 272, 37386


def read_picture(path, clock_utc_offset_h=0.0):
    """(image as float32, FITS header) of an ordinary picture (JPEG, PNG, TIFF, ... from a phone or a camera).
    Colour pictures become one brightness image (0.2126 R + 0.7152 G + 0.0722 B); rows are turned so the top of
    the picture is at the top on screen (FITS rows count upwards). From the EXIF data: the time (camera clock minus
    clock_utc_offset_h), exposure, ISO, camera and focal length.

    8-bit pictures are nearly always gamma-encoded and processed by the camera: fine for viewing, stacking and
    star positions, not for accurate photometry (raw files are); the header says so (LINEAR = F)."""
    path = Path(path)
    exif = {}
    if path.suffix.lower() in (".tif", ".tiff"):
        import tifffile

        data = tifffile.imread(path)
    else:
        from PIL import Image

        with Image.open(path) as im:
            ex = im.getexif()
            exif = dict(ex) | dict(ex.get_ifd(_EXIF_IFD))
            if im.mode not in ("L", "I", "I;16", "F", "RGB"):
                im = im.convert("RGB")
            data = np.asarray(im)
    data = np.asarray(data)
    bits = 8 * data.dtype.itemsize if data.dtype.kind in "ui" else 32
    while data.ndim > 2 and data.shape[-1] not in (3, 4) and data.shape[0] in (3, 4):
        data = np.moveaxis(data, 0, -1)  # planes first (some TIFF writers)
    if data.ndim == 3:
        rgb = data[..., :3].astype(np.float32)
        data = rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722
    if data.ndim != 2:
        raise ValueError(f"{path.name}: not a 2-D picture (shape {data.shape})")
    h = fits.Header()
    h["PICTURE"] = (path.name, "converted from an ordinary picture")
    h["LINEAR"] = (bits > 8, "8-bit pictures are gamma-encoded: not for accurate photometry")
    if exif.get(_EXPOSURE):
        h["EXPTIME"] = (float(exif[_EXPOSURE]), "[s] from the EXIF data")
    if exif.get(_ISO):
        iso = exif[_ISO]
        h["ISOSPEED"] = (float(iso[0] if isinstance(iso, tuple) else iso), "ISO setting")
    if exif.get(_MODEL):
        h["INSTRUME"] = (str(exif[_MODEL]).strip()[:60], "camera")
    if exif.get(_FOCAL):
        h["FOCALLEN"] = (float(exif[_FOCAL]), "[mm] focal length")
    if exif.get(_DATE_ORIGINAL):
        from datetime import datetime

        try:
            stamp = datetime.strptime(str(exif[_DATE_ORIGINAL]).strip(), "%Y:%m:%d %H:%M:%S")
            h["DATE-CAM"] = (stamp.isoformat(), "camera clock (EXIF)")
            utc = stamp - timedelta(hours=float(clock_utc_offset_h))
            h["DATE-OBS"] = (utc.isoformat(), f"UTC = camera clock - {clock_utc_offset_h:g} h")
        except ValueError:  # an odd date format: no time rather than a wrong one
            pass
    h["CLKOFFS"] = (float(clock_utc_offset_h), "[h] camera clock minus UTC, given by the user")
    return np.ascontiguousarray(data[::-1]).astype(np.float32), h


def is_fits(path):
    return str(path).lower().endswith(FITS_SUFFIXES)


def _is_cube(path):
    from .fits import find_image_hdu

    with fits.open(path) as hdul:
        return int(hdul[find_image_hdu(hdul)].header.get("NAXIS", 2)) > 2


CLOCK_UTC_OFFSET_H = 0.0  # camera clock - UTC for files opened in the interface (set from the user's settings)


def fits_copy(path, clock_utc_offset_h=None):
    """The file itself when it is FITS; for a camera raw file or a picture, a FITS copy in fits_from_raw next to
    it (made once, kept while the original is unchanged), so every tool can work on it. The time is the camera
    clock minus clock_utc_offset_h (default: CLOCK_UTC_OFFSET_H)."""
    if clock_utc_offset_h is None:
        clock_utc_offset_h = CLOCK_UTC_OFFSET_H
    path = Path(path)
    cube = is_fits(path) and _is_cube(path)
    if is_fits(path) and not cube:
        return path
    stem = next((path.name[: -len(x)] for x in FITS_SUFFIXES if path.name.lower().endswith(x)), path.stem)
    target = path.parent / "fits_from_raw" / (stem + ".fits")
    if cube:  # a 3-D FITS (colour cube, a stack of one plane): the 2-D image every tool works on
        from .fits import find_image_hdu, plane

        if not (target.exists() and target.stat().st_mtime >= path.stat().st_mtime):
            with fits.open(path) as hdul:
                hdu = hdul[find_image_hdu(hdul)]
                data, h = np.asarray(plane(hdu.data), np.float32), hdu.header.copy()
            for key in ("NAXIS3", "NAXIS4", "CTYPE3", "CRPIX3", "CRVAL3", "CDELT3", "CUNIT3"):
                h.remove(key, ignore_missing=True)
            h.add_history(f"2-D image from the cube {path.name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            fits.PrimaryHDU(data, h).writeto(target, overwrite=True, output_verify="silentfix")
        return target
    if target.exists() and target.stat().st_mtime >= path.stat().st_mtime:
        if fits.getheader(target).get("CLKOFFS") == float(clock_utc_offset_h):
            return target
    data, h = (
        read_raw(path, clock_utc_offset_h)
        if path.suffix.lower() in RAW_SUFFIXES
        else read_picture(path, clock_utc_offset_h)
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    fits.PrimaryHDU(data, h).writeto(target, overwrite=True, output_verify="silentfix")
    return target


def fits_paths(paths, clock_utc_offset_h=None):
    """FITS paths for a selection of files of any kind (see fits_copy); a file that cannot be read is left out
    with a warning instead of stopping the rest."""
    import warnings

    out = []
    for p in paths:
        try:
            out.append(str(fits_copy(p, clock_utc_offset_h)))
        except Exception as e:  # e.g. a damaged file among many
            warnings.warn(f"{Path(p).name}: {type(e).__name__}: {e}", stacklevel=2)
    return out


def convert_raw_folder(folder, out_dir=None, clock_utc_offset_h=0.0, progress=None):
    """Every camera raw file and picture under folder -> FITS under out_dir (default folder/fits_from_raw), keeping the
    sub-folders; IMAGETYP from the folder names. Files already converted with the same clock offset are kept.
    Returns (written paths, problems)."""
    folder = Path(folder)
    out_dir = Path(out_dir) if out_dir else folder / "fits_from_raw"
    found = [p for p in folder.rglob("*") if p.is_file() and out_dir not in p.parents]
    has_frames = any(is_fits(p) or p.suffix.lower() in RAW_SUFFIXES for p in found)
    # pictures are frames only in a night of pictures (a phone): next to FITS or raw frames they are previews and
    # exports (the application's own PNG / JPEG among them), which must not be calibrated as frames
    suffixes = RAW_SUFFIXES if has_frames else RAW_SUFFIXES + PICTURE_SUFFIXES
    files = sorted(p for p in found if p.suffix.lower() in suffixes)
    written, problems = [], []
    for n, p in enumerate(files):
        if progress:
            progress(n / max(1, len(files)), p.name)
        target = out_dir / p.relative_to(folder).with_suffix(".fits")
        try:
            if target.exists() and fits.getheader(target).get("CLKOFFS") == float(clock_utc_offset_h):
                written.append(str(target))
                continue
            reader = read_raw if p.suffix.lower() in RAW_SUFFIXES else read_picture
            data, h = reader(p, clock_utc_offset_h)
            kind = _kind_from_path(p, folder)
            if kind:
                h["IMAGETYP"] = (kind, "from the folder name")
            target.parent.mkdir(parents=True, exist_ok=True)
            fits.PrimaryHDU(data, h).writeto(target, overwrite=True, output_verify="silentfix")
            written.append(str(target))
        except Exception as e:  # one unreadable file must not stop the night
            problems.append((str(p), f"{type(e).__name__}: {e}"))
    return written, problems
