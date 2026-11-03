"""Frame catalogue: read FITS headers and classify frames as bias / dark / flat / light.

Header conventions differ between capture programs (MaxIm DL, N.I.N.A., SharpCap, KStars,
IRAF, observatory pipelines), so several keywords and spellings are accepted. When the
header says nothing, the file name decides; a zero exposure is a bias.
"""

import re
from dataclasses import asdict, dataclass
from pathlib import Path

from astropy.io import fits

from ..hdr import number
from ..io.fits import find_image_hdu

KINDS = ("bias", "dark", "flat", "light")
FITS_SUFFIXES = (".fits", ".fit", ".fts", ".fits.gz", ".fit.gz", ".fts.gz", ".fits.fz")

_TYPE_KEYS = ("IMAGETYP", "IMAGETYPE", "FRAME", "FRAMETYP", "OBSTYPE", "EXPTYPE")
_PATTERNS = [  # order matters: "dark flat" is a dark for the flat, "flat dark" too
    ("dark", re.compile(r"dark", re.I)),
    ("bias", re.compile(r"bias|zero|offset", re.I)),
    ("flat", re.compile(r"flat|sky ?flat|dome ?flat|twilight", re.I)),
    ("light", re.compile(r"light|object|science|sci\b|target", re.I)),
]


@dataclass
class Frame:
    path: str
    kind: str  # bias | dark | flat | light | unknown
    exptime: float | None
    filter: str | None
    temperature: float | None  # sensor temperature, deg C
    binning: tuple[int, int]
    shape: tuple[int, int]
    readout: str  # gain/offset/readout mode: frames only match when equal
    date_obs: str | None
    object: str | None

    def as_dict(self):
        return asdict(self)


def _first(header, *keys):
    for k in keys:
        if k in header and header[k] not in (None, ""):
            return header[k]
    return None


def _float(v):
    return number(v)  # '10 s', '-95.5 C' ... as some capture programs write them


def classify(header, filename: str = "") -> str:
    for text in [str(_first(header, k) or "") for k in _TYPE_KEYS] + [Path(filename).name]:
        for kind, pattern in _PATTERNS:
            if text and pattern.search(text):
                return kind
    exptime = _float(_first(header, "EXPTIME", "EXPOSURE"))
    if exptime == 0:
        return "bias"
    return "unknown"


def read_frame(path: Path) -> Frame:
    with fits.open(path, memmap=True) as hdul:
        hdu = hdul[find_image_hdu(hdul)]
        h = hdu.header
        shape = tuple(int(n) for n in hdu.shape[-2:])
        cube = len(hdu.shape) > 2
    if cube:  # colour cubes and one-plane cubes: calibrated as their 2-D image (a copy in fits_from_raw)
        from ..io.bayer import fits_copy

        return read_frame(fits_copy(path))
    readout = "/".join(f"{k}={h[k]}" for k in ("GAIN", "EGAIN", "OFFSET", "READOUTM", "READMODE") if k in h)
    filt = _first(h, "FILTER", "FILTER1", "FILTNAME", "FILTERS")
    return Frame(
        path=str(path),
        kind=classify(h, str(path)),
        exptime=_float(_first(h, "EXPTIME", "EXPOSURE", "EXP_TIME")),
        filter=str(filt).strip() if filt is not None else None,
        temperature=_float(_first(h, "CCD-TEMP", "CCD_TEMP", "SENSOR-T", "DET-TEMP", "SET-TEMP")),
        binning=(
            int(_float(_first(h, "XBINNING", "BINX", "CCDXBIN")) or 1),
            int(_float(_first(h, "YBINNING", "BINY", "CCDYBIN")) or 1),
        ),
        shape=shape,
        readout=readout,
        date_obs=_first(h, "DATE-OBS", "DATE_OBS"),
        object=_first(h, "OBJECT"),
    )


def scan(folder: Path, recursive: bool = True) -> tuple[list[Frame], list[tuple[str, str]]]:
    """Return (frames, problems). Unreadable files are reported, never fatal."""
    files = sorted(
        p
        for p in (Path(folder).rglob("*") if recursive else Path(folder).iterdir())
        if p.is_file() and p.name.lower().endswith(FITS_SUFFIXES)
    )
    frames, problems = [], []
    for p in files:
        try:
            frames.append(read_frame(p))
        except Exception as e:  # corrupt/truncated file: list it, continue with the rest
            problems.append((str(p), f"{type(e).__name__}: {e}"))
    return frames, problems
