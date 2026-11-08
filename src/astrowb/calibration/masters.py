"""Master bias / dark / flat and light-frame calibration.

Formulas (as in IRAF ccdred, ccdproc and MaxIm DL):
  master bias  = clipped mean of bias frames
  master dark  = clipped mean of (dark - master bias)            [BIASSUB = True]
                 or of raw darks when no bias is given           [BIASSUB = False]
  master flat  = clipped mean of (flat - bias - scaled dark) / median(that frame),
                 normalised to median 1
  calibrated   = (light - bias - dark * t_light / t_dark) / flat
                 or (light - raw dark) / flat when a raw dark has the light's exposure time

Frames are read in row blocks through ``HDU.section`` so a stack of large frames never has
to fit in memory; the combine runs on the GPU when it helps (see compute/combine.py).

Overscan and trimming (IRAF ccdproc): when a frame's header has BIASSEC (the overscan strip) the bias level
read in it is subtracted, and when it has TRIMSEC (or DATASEC) only that part is kept — at reading time, so
masters, lights and everything later see the same corrected, trimmed geometry. The level is fitted row by row
(column by column for a strip along the bottom or top), as IRAF's overscan fit and ccdproc's subtract_overscan
do: the median across the strip for each row, then a cubic polynomial along the rows with 3-sigma clipping.
A stable bias gives a flat fit (the same as one level); bias structure along the readout is followed.

Dark optimisation (as MaxIm DL's auto-optimise): the dark scale k that leaves the least variance in
light - bias - k * dark is the least-squares solution k = cov(light - bias, dark) / var(dark); stars and sky do
not correlate with the dark, hot pixels do, so k measures the dark current actually in the light.

Defect map: hot pixels are those of the master dark above median + HOT_SIGMA x robust sigma; cold (dead)
pixels those of the master flat below COLD_LEVEL of the median. They are replaced in each calibrated light by
the median of their good neighbours (3 x 3, then 5 x 5), as IRAF fixpix / MaxIm DL's defect map do.

Linearity correction (as AstroImageJ's): with `linearity(c0, c1, c2, ...)` in effect every raw pixel value v is
replaced by c0 + c1 v + c2 v^2 + ... when it is read — before overscan, bias, dark and flat, since the detector's
non-linearity acts on the counts it read out. The coefficients come from a series of flats of rising exposure
(the camera maker's sheet, or AIJ / a linearity test); without them nothing is changed.
"""

import contextlib
import contextvars
import re
import warnings
from pathlib import Path

import numpy as np
from astropy.io import fits

from ..compute.combine import clipped_mean
from ..hdr import get, number
from ..io.fits import find_image_hdu, inherited
from ..io.lzw import readable

MEMORY_BUDGET = 512 * 2**20  # bytes of float32 stack per block
EXPTIME_RTOL = 0.01  # exposure times within 1 % count as equal
_COPY_KEYS = (
    "XBINNING",
    "YBINNING",
    "GAIN",
    "EGAIN",
    "OFFSET",
    "READOUTM",
    "READMODE",
    "INSTRUME",
    "CCD-TEMP",
    "SET-TEMP",
    "FILTER",
    "EXPTIME",
    "TELESCOP",
    "DATE-OBS",
)


HOT_SIGMA = 8.0
COLD_LEVEL = 0.5
DEAD_FLAT = 0.05  # flat response below 5 % of the median: a dead column or the chip's masked edge, not light


class CalibrationError(ValueError):
    pass


def section(text):
    """A FITS / IRAF section '[x1:x2,y1:y2]' (1-based, inclusive) as numpy (row, column) slices, or None. An axis
    written '*' or ':' is the whole axis (MaxIm DL writes TRIMSEC '[1:4096, :]'); a section with one axis only
    ('[4096:4109]') says nothing about the other and is not used."""
    axis = r"\s*(?:(\d+)\s*:\s*(\d+)|\*|:)\s*"
    m = re.fullmatch(rf"\s*\[{axis},{axis}\]\s*", str(text))
    if not m:
        return None
    x1, x2, y1, y2 = (None if v is None else int(v) for v in m.groups())
    rows = slice(None) if y1 is None else slice(min(y1, y2) - 1, max(y1, y2))
    return rows, slice(None) if x1 is None else slice(min(x1, x2) - 1, max(x1, x2))


def overscan_level(strip, over, trim, order=3, clip=3.0):
    """Bias level for every row (or column) of the trimmed frame, from the overscan strip: medians across the
    strip, a clipped polynomial fit along it. Shape (rows, 1) for a strip of columns, (1, columns) for a strip
    of rows, so it broadcasts over the trimmed data."""
    along_rows = strip.shape[0] >= strip.shape[1]  # tall strip: extra columns at the end of every row
    prof = np.median(strip, axis=1 if along_rows else 0)
    pos = np.arange(over[0 if along_rows else 1].start, over[0 if along_rows else 1].stop)[: prof.size]
    target = np.arange((trim[0] if along_rows else trim[1]).start, (trim[0] if along_rows else trim[1]).stop)
    keep = np.isfinite(prof)
    deg = min(order, max(0, keep.sum() // 10))  # short strips: lower order (a constant for a few rows)
    scale = max(1.0, float(np.ptp(pos)))
    for _ in range(5):
        coef = np.polyfit((pos[keep] - pos.mean()) / scale, prof[keep], deg)
        r = prof - np.polyval(coef, (pos - pos.mean()) / scale)
        sd = 1.4826 * np.median(np.abs(r[keep]))
        new = np.isfinite(prof) & (np.abs(r) <= clip * max(sd, 1e-6))
        if np.array_equal(new, keep) or new.sum() <= deg + 1:
            break
        keep = new
    level = np.polyval(coef, (target - pos.mean()) / scale).astype(np.float32)
    return level[:, None] if along_rows else level[None, :]


_LINEARITY = contextvars.ContextVar("linearity", default=None)


@contextlib.contextmanager
def linearity(coefficients):
    """Apply the polynomial c0 + c1 v + c2 v^2 + ... to every raw value read inside this block (None or []: off)."""
    c = [float(x) for x in coefficients or []]
    if c and (len(c) < 2 or c[1] <= 0):
        raise CalibrationError("linearity coefficients: give at least c0 and c1, with c1 > 0")
    token = _LINEARITY.set(np.asarray(c[::-1], np.float64) if c else None)
    try:
        yield
    finally:
        _LINEARITY.reset(token)


def _linear(values):
    poly = _LINEARITY.get()
    return values if poly is None else np.polyval(poly, values).astype(np.float32)


def _without_overscan(trim, over):
    """The data section without the overscan strip, when a header's DATASEC also covers the BIASSEC columns
    (or rows): the strip is cut off the side it is on, as the frame's own TRIMSEC would."""
    if not over:
        return trim
    rows, cols = trim
    (o_r, o_c), n_r, n_c = over, rows.stop - rows.start, cols.stop - cols.start
    if o_r.stop - o_r.start >= n_r / 2:  # a strip of columns
        if cols.start < o_c.start < cols.stop:  # on the right
            cols = slice(cols.start, o_c.start)
        elif o_c.start <= cols.start < o_c.stop < cols.stop:  # on the left
            cols = slice(o_c.stop, cols.stop)
    elif o_c.stop - o_c.start >= n_c / 2:  # a strip of rows
        if rows.start < o_r.start < rows.stop:  # at the top
            rows = slice(rows.start, o_r.start)
        elif o_r.start <= rows.start < o_r.stop < rows.stop:  # at the bottom
            rows = slice(o_r.stop, rows.stop)
    return rows, cols


def _layout(hdu):
    """(rows, columns, overscan level) of a frame from BIASSEC and TRIMSEC / DATASEC in its header; the level is
    0 or an array that broadcasts over the trimmed frame (see overscan_level)."""
    h = hdu.header
    ny, nx = hdu.shape[-2:]

    def whole(sec):  # "the whole axis" made concrete: the code below reads .start and .stop
        if sec and any(s.stop is not None and s.stop > n for s, n in zip(sec, (ny, nx), strict=True)):
            return None  # outside the frame: the raw frame's section, left in the header of a trimmed one (LCO e91)
        return sec and (slice(*sec[0].indices(ny)[:2]), slice(*sec[1].indices(nx)[:2]))

    over = whole(section(h.get("BIASSEC", "")))
    # the first section that can be read: some pipelines write TRIMSEC = 'UNKNOWN' (LCO FLOYDS)
    trim = next((t for t in (whole(section(h.get(k, ""))) for k in ("TRIMSEC", "DATASEC")) if t), None)
    if not over and not trim:
        over, trim = _eso_sections(h, ny, nx) or (None, None)
    trim = _without_overscan(trim or (slice(0, ny), slice(0, nx)), over)
    level = overscan_level(_linear(np.asarray(hdu.section[over], np.float32)), over, trim) if over else np.float32(0.0)
    return trim[0], trim[1], level


def _eso_sections(h, ny, nx):
    """(overscan, data) sections of a single-output ESO detector from its prescan / overscan sizes (HARPS, FEROS,
    UVES and EFOSC2 write no BIASSEC; a raw HARPS chip carries 245 ADU of bias), or None when they do not add up
    to this frame."""
    px, ox, py, oy = (int(get(h, f"ESO DET OUT1 {k}", default=0)) for k in ("PRSCX", "OVSCX", "PRSCY", "OVSCY"))
    dx, dy = get(h, "ESO DET OUT1 NX"), get(h, "ESO DET OUT1 NY")
    if dx is None or dy is None or px + int(dx) + ox != nx or py + int(dy) + oy != ny or not (px or ox or py or oy):
        return None
    rows, cols = slice(py, ny - oy), slice(px, nx - ox)
    if ox or px:  # a strip of columns, the overscan preferred
        return (rows, slice(nx - ox, nx) if ox else slice(0, px)), (rows, cols)
    return (slice(ny - oy, ny) if oy else slice(0, py), cols), (rows, cols)


def _corrected_header(header, layout):
    out = header.copy()
    if "BIASSEC" in header:
        out["OVERSCAN"] = (float(np.mean(layout[2])), f"mean overscan level subtracted ({header['BIASSEC']})")
    elif np.any(layout[2]):
        out["OVERSCAN"] = (float(np.mean(layout[2])), "mean ESO prescan / overscan level subtracted")
    r0, c0 = layout[0].start or 0, layout[1].start or 0
    if (r0 or c0) and "BAYERPAT" in out:  # the colour pattern now starts at the first kept pixel
        out["XBAYROFF"] = (int(get(out, "XBAYROFF", default=0)) + c0) % 2
        out["YBAYROFF"] = (int(get(out, "YBAYROFF", default=0)) + r0) % 2
    for axis, start in ((1, c0), (2, r0)):
        if start and f"CRPIX{axis}" in out:
            out[f"CRPIX{axis}"] = float(out[f"CRPIX{axis}"]) - start
    for key in ("TRIMSEC", "DATASEC", "BIASSEC"):
        if key in out:
            out.add_history(f"{key} {header[key]} applied")
            del out[key]
    return out


def _open(paths):
    hduls = [fits.open(readable(p)) for p in paths]  # lazy; memmap=True would refuse BZERO-scaled data
    hdus = [h[find_image_hdu(h)] for h in hduls]
    for h in hdus:
        h.layout = _layout(h)
    shapes = {(h.layout[0].stop - h.layout[0].start, h.layout[1].stop - h.layout[1].start) for h in hdus}
    if len(shapes) != 1:
        for h in hduls:
            h.close()
        raise CalibrationError(f"frames have different sizes: {sorted(shapes)}")
    return hduls, hdus, shapes.pop()


def _rows(hdu, r0, r1):
    rows, cols, level = hdu.layout
    if np.ndim(level) and level.shape[0] > 1:  # one level per row: the block's rows
        level = level[r0:r1]
    return _linear(np.asarray(hdu.section[rows.start + r0 : rows.start + r1, cols], dtype=np.float32)) - level


def combine_files(paths, prepare=None, sigma=3.0, maxiters=5, ctx=None):
    """Clipped-mean combine of FITS files. prepare(i, block, r0, r1) -> corrected float32 block.

    Returns (image, kept_count, device_used)."""
    paths = [str(p) for p in paths]
    if not paths:
        raise CalibrationError(
            "no frames to combine: check the folder and the frame types listed in the Calibration window"
        )
    hduls, hdus, (ny, nx) = _open(paths)
    try:
        rows = max(1, MEMORY_BUDGET // (len(paths) * nx * 4))
        out, cnt, used = np.empty((ny, nx), np.float32), np.empty((ny, nx), np.int32), set()
        for r0 in range(0, ny, rows):
            r1 = min(ny, r0 + rows)
            stack = np.stack(
                [prepare(i, _rows(h, r0, r1), r0, r1) if prepare else _rows(h, r0, r1) for i, h in enumerate(hdus)]
            )
            out[r0:r1], cnt[r0:r1], dev = clipped_mean(stack, sigma, maxiters)
            used.add(dev)
            if ctx:
                ctx.check()
                ctx.progress(r1 / ny, "combining")
        return out, cnt, "+".join(sorted(used))
    finally:
        for h in hduls:
            h.close()


def _header(paths, kind, extra):
    with fits.open(readable(paths[0])) as hdul:
        src = inherited(hdul, find_image_hdu(hdul))
    h = fits.Header()
    for k in _COPY_KEYS:
        if k in src:
            h[k] = src[k]
    h["IMAGETYP"] = f"Master {kind}"
    h["NCOMBINE"] = (len(paths), "number of frames combined")
    h["COMBINE"] = ("sigma-clipped mean", "combine method")
    for k, v in extra.items():
        h[k] = v
    for p in paths:
        h.add_history(f"input: {Path(p).name}")
    return h


def _exptime(path):
    with fits.open(readable(path)) as hdul:
        h = inherited(hdul, find_image_hdu(hdul))
        t = get(h, "EXPTIME", "EXPOSURE")
    if t is None:
        raise CalibrationError(f"{Path(path).name}: no EXPTIME")
    return t


def load(path, crop=None):
    """The frame as float32, overscan-subtracted and trimmed when its header says how (BIASSEC, TRIMSEC).
    crop: (y0, y1, x0, x1) of the trimmed frame, only that part read (cut at the frame's edge): a tile-compressed
    frame decompresses only the tiles it touches."""
    from ..io.lzw import readable

    with fits.open(readable(path)) as hdul:
        i = find_image_hdu(hdul)
        hdu = hdul[i]
        rows, cols, level = lay = _layout(hdu)
        if crop is None:
            data = _linear(np.asarray(hdu.data, dtype=np.float32)[..., rows, cols]) - level
        else:
            y0, y1, x0, x1 = (int(v) for v in crop)
            if np.ndim(level) == 2:  # a column or a row of overscan levels
                level = level[y0:y1] if level.shape[0] > 1 else level[:, x0:x1]
            rows = slice(rows.start + y0, min(rows.stop, rows.start + y1))
            cols = slice(cols.start + x0, min(cols.stop, cols.start + x1))
            part = hdu.section[rows, cols] if len(hdu.shape) == 2 else hdu.data[..., rows, cols]
            data = _linear(np.asarray(part, dtype=np.float32)) - level
        header = _corrected_header(inherited(hdul, i), lay)
        if _LINEARITY.get() is not None:
            header["LINCORR"] = (True, "linearity correction applied to the raw counts")
        return data, header


def master_bias(paths, sigma=3.0, ctx=None):
    img, _, dev = combine_files(paths, sigma=sigma, ctx=ctx)
    return img, _header(paths, "Bias", {"EXPTIME": 0.0, "SIGCLIP": sigma, "DEVICE": dev})


def master_dark(paths, bias=None, sigma=3.0, ctx=None):
    """bias: master bias array or None."""
    times = {_exptime(p) for p in paths}
    if max(times) - min(times) > EXPTIME_RTOL * max(times):
        raise CalibrationError(f"darks with different exposure times cannot be combined: {sorted(times)}")
    prep = (lambda i, b, r0, r1: b - bias[r0:r1]) if bias is not None else None
    img, _, dev = combine_files(paths, prep, sigma=sigma, ctx=ctx)
    return img, _header(
        paths,
        "Dark",
        {"EXPTIME": float(np.mean(sorted(times))), "BIASSUB": bias is not None, "SIGCLIP": sigma, "DEVICE": dev},
    )


def dark_for(exptime, bias, dark, dark_header):
    """The dark signal (bias excluded) for an exposure time, or None. Raises if it cannot be made."""
    if dark is None:
        return None
    t_dark = number(dark_header["EXPTIME"], 0.0)
    if dark_header.get("BIASSUB", False):
        return dark * np.float32(exptime / t_dark) if t_dark > 0 else None
    if abs(exptime - t_dark) <= EXPTIME_RTOL * max(exptime, t_dark):
        return dark if bias is None else dark - bias  # raw dark contains the bias
    raise CalibrationError(
        f"dark ({t_dark} s) without bias subtraction cannot be scaled to {exptime} s; "
        "add bias frames or darks with the same exposure"
    )


def master_flat(paths, bias=None, dark=None, dark_header=None, sigma=3.0, ctx=None):
    corr = []
    for p in paths:  # per-frame level: median of the corrected frame
        data, h = load(p)
        d = dark_for(_exptime(p), bias, dark, dark_header)
        frame = data - (bias if bias is not None else 0) - (d if d is not None else 0)
        level = float(np.median(frame[::4, ::4]))
        if not level > 0:
            raise CalibrationError(f"{Path(p).name}: flat level {level:.3g} is not positive")
        corr.append((d, np.float32(1 / level)))

    def prep(i, block, r0, r1):
        d, scale = corr[i]
        if bias is not None:
            block = block - bias[r0:r1]
        if d is not None:
            block = block - d[r0:r1]
        return block * scale

    img, _, dev = combine_files(paths, prep, sigma=sigma, ctx=ctx)
    img /= np.float32(np.nanmedian(img))
    return img, _header(paths, "Flat", {"SIGCLIP": sigma, "DEVICE": dev, "NORMALIZ": (True, "median = 1")})


def dark_scale(light_minus_bias, dark_signal):
    """Least-squares dark scale k minimising the variance of light - bias - k * dark (finite pixels)."""
    a, d = np.asarray(light_minus_bias, float)[::2, ::2], np.asarray(dark_signal, float)[::2, ::2]
    ok = np.isfinite(a) & np.isfinite(d)
    a, d = a[ok] - a[ok].mean(), d[ok] - d[ok].mean()
    var = (d * d).sum()
    return float(np.clip((a * d).sum() / var, 0.0, 5.0)) if var > 0 else 1.0


def defect_map(dark=None, flat=None, hot_sigma=HOT_SIGMA, cold_level=COLD_LEVEL):
    """Boolean map of hot (from the master dark) and cold / dead (from the master flat) pixels."""
    bad = np.zeros((dark if dark is not None else flat).shape, bool)
    if dark is not None:
        sample = dark[::2, ::2][np.isfinite(dark[::2, ::2])]
        med = np.median(sample)
        sigma = 1.4826 * np.median(np.abs(sample - med))
        bad |= dark > med + hot_sigma * max(sigma, 1e-6)
    if flat is not None:
        bad |= ~(flat > cold_level * np.nanmedian(flat))
    return bad


def repair(data, bad):
    """Replace the pixels marked bad by the median of their good neighbours (3 x 3, else 5 x 5)."""
    out = np.asarray(data, np.float32).copy()
    work = np.where(bad, np.nan, out)
    todo = np.asarray(bad, bool).copy()
    for size in (3, 5):
        ys, xs = np.nonzero(todo)
        if not len(ys):
            break
        h = size // 2
        pad = np.pad(work, h, constant_values=np.nan)
        windows = np.stack([pad[ys + dy, xs + dx] for dy in range(size) for dx in range(size)])
        with np.errstate(all="ignore"), warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)  # a window with no good pixel: left for the larger one
            fill = np.nanmedian(windows, axis=0)
        ok = np.isfinite(fill)
        out[ys[ok], xs[ok]] = work[ys[ok], xs[ok]] = fill[ok]
        todo[ys[ok], xs[ok]] = False
    return out


def calibrate(light, exptime, bias=None, dark=None, dark_header=None, flat=None, dark_factor=1.0, defects=None):
    """Return the calibrated float32 frame. Any of bias/dark/flat may be None (step skipped).
    dark_factor: extra scale of the dark (see dark_scale); defects: boolean map of pixels to repair."""
    out = np.asarray(light, np.float32)
    d = dark_for(exptime, bias, dark, dark_header)  # dark signal without bias
    if bias is not None:
        out = out - bias
    if d is not None:
        out = out - d * np.float32(dark_factor)
    if flat is not None:
        live = flat > DEAD_FLAT * np.nanmedian(flat[::4, ::4])  # IRAF ccdproc's minreplace, ccdproc's min_value
        with np.errstate(divide="ignore", invalid="ignore"):
            out = np.where(live, out / flat, np.nan).astype(np.float32)  # dead flat pixels -> NaN, not 1e8
    if defects is not None:
        out = repair(out, defects)
    return out


def save(path, data, header):
    # headers come from the camera files, and some capture programs break the FITS rules (lower-case keywords,
    # values like NaN or 1.0.0): astropy refuses to write those unless told to fix them
    fits.PrimaryHDU(np.asarray(data, np.float32), header).writeto(path, overwrite=True, output_verify="silentfix")
    return str(path)
