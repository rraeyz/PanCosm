"""What a spectrum file's header says before it is reduced: calibrated (bias and dark off) or raw, extracted (1-D)
or a 2-D frame. The Spectroscopy window's file rows ask on every typed character, so answers are remembered while the
file is unchanged."""


def by_stat(fn):
    """fn(path) remembered while the file read (the path, or its decompressed copy) is unchanged: the file rows ask
    on every typed character, and each header read of a compressed frame cost tens of ms (typing an arc path froze
    the window for a second)."""
    import functools
    import os

    from ..io.lzw import ready_copy

    remembered = functools.lru_cache(maxsize=256)(lambda path, _read, _mtime, _size: fn(path))

    @functools.wraps(fn)
    def wrapper(path):
        try:
            read = ready_copy(path)  # None: a .fits.Z not decompressed yet, asked again until it is
            st = os.stat(read)
        except (OSError, TypeError, ValueError):
            return fn(path)
        return remembered(str(path), str(read), st.st_mtime_ns, st.st_size)

    return wrapper


@by_stat
def calibrated(path):
    """True when a frame's header says bias / dark were taken off (this program's Calibrate page: CALB / CALD; IRAF
    ccdproc: ZEROCOR / DARKCOR / CCDPROC); False for a raw frame; None when it cannot be read."""
    from astropy.io import fits

    from ..io.lzw import ready_copy

    path = ready_copy(path)  # ESO's .fits.Z: astropy alone needs a package we do not ship (it crashed the tab)
    if path is None:
        return None
    try:
        with fits.open(path) as h:
            keys = set(h[0].header) | (set(h[1].header) if len(h) > 1 else set())
    except (OSError, ValueError):
        return None
    return bool(keys & {"CALB", "CALD", "ZEROCOR", "DARKCOR", "CCDPROC"})


@by_stat
def extracted(path):
    """True when the file is already extracted (a 1-D spectrum, IRAF apall output, a pipeline's e2ds): only the
    wavelength calibration is left to do."""
    from astropy.io import fits

    from ..io.lzw import ready_copy
    from .steps import looks_extracted

    path = ready_copy(path)  # a raw .fits.Z not yet decompressed: raw frames are not extracted spectra
    if path is None:
        return False
    try:
        with fits.open(path) as h:
            return any(x.is_image and x.header.get("NAXIS", 0) >= 1 and looks_extracted(x.header) for x in h[:2])
    except (OSError, ValueError):
        return False
