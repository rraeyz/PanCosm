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
from ..io.fits import find_image_hdu, inherited
from ..io.lzw import readable

KINDS = ("bias", "dark", "flat", "light")
FITS_SUFFIXES = (".fits", ".fit", ".fts", ".fits.gz", ".fit.gz", ".fts.gz", ".fits.fz")

_TYPE_KEYS = ("IMAGETYP", "IMAGETYPE", "FRAME", "FRAMETYP", "OBSTYPE", "EXPTYPE", "HIERARCH ESO DPR TYPE")
_PATTERNS = [  # order matters: "dark flat" is a dark for the flat, "flat dark" too
    ("dark", re.compile(r"dark", re.I)),
    ("bias", re.compile(r"bias|zero|offset", re.I)),
    ("flat", re.compile(r"flat|sky ?flat|dome ?flat|twilight", re.I)),
    # wavelength-calibration lamps (IRAF 'comp'): calibrated like lights, never divided by a flat nor stacked
    ("arc", re.compile(r"(?<![a-z])(comp|arc|lamp|thar|th-ar|fear|hear|cuar|neon|argon|wavecal|wave)(?![a-z])", re.I)),
    # ESO: STD = a standard; LCO: EXPOSE (imaging), SPECTRUM (FLOYDS), STANDARD
    ("light", re.compile(r"light|object|science|sci\b|target|expose|spectrum|standard|(?<![a-z])std(?![a-z])", re.I)),
]


@dataclass
class Frame:
    path: str
    kind: str  # bias | dark | flat | light | arc | unknown
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


_FIBRES = {"STAR": "light", "SKY": "light", "WAVE": "arc", "FP": "arc", "BIAS": "bias", "DARK": "dark", "LAMP": "flat"}


def _fibre_kind(text):
    """The kind of a fibre-fed ESO frame from its DPR TYPE 'fibre A,fibre B[,lamp]' (HARPS: 'STAR,WAVE,G8' is a star
    with the ThAr reference beside it, 'LAMP,DARK,TUN' the tungsten flat of fibre A): fibre A, the science fibre,
    decides; a frame lit in fibre B only is no frame for fibre A. None when the text is not of this form (UVES
    'LAMP,FLAT', 'LAMP,WAVE' are left to the patterns)."""
    t = [s.strip().upper() for s in str(text).split(",")]
    if len(t) < 2 or t[0] not in _FIBRES or t[1] not in _FIBRES or (t[0] == "LAMP" and "TUN" not in t[2:]):
        return None
    return "unknown" if t[0] == "DARK" and t[1] != "DARK" else _FIBRES[t[0]]


def classify(header, filename: str = "") -> str:
    if kind := _fibre_kind(_first(header, "HIERARCH ESO DPR TYPE") or ""):
        return kind
    stated = [str(_first(header, k) or "").strip() for k in _TYPE_KEYS]
    for text in stated + [Path(filename).name]:
        for kind, pattern in _PATTERNS:
            if text and pattern.search(text):
                return kind
    exptime = _float(_first(header, "EXPTIME", "EXPOSURE"))
    if exptime == 0:
        return "bias"
    # observers name the science frames after the star (nsvs01286630_001.fits, NY_Vir_V_012.fit): a frame that says
    # nothing of a type is a light; only a type the header states and we do not know (FOCUS, TEST, ACQUIRE) is left
    # out — the user can change any type in the Calibration window
    return "unknown" if any(stated) else "light"


def rule_kind(header, rules):
    """The kind the first matching user rule gives ({"key", "value", "kind"}, values compared without case), or
    None."""
    for r in rules:
        value = header.get(str(r["key"]).strip().upper())
        if value is not None and str(value).strip().lower() == str(r["value"]).strip().lower():
            return r["kind"]
    return None


def why(header, filename="", rules=()):
    """In words, what decided the frame's kind: a user rule, a keyword, the file name or the exposure."""
    for r in rules:
        if rule_kind(header, [r]):
            return f"your rule: {r['key']} = {r['value']} is a {r['kind']}"
    if kind := _fibre_kind(_first(header, "HIERARCH ESO DPR TYPE") or ""):
        return f"HIERARCH ESO DPR TYPE says {kind}"
    for key in _TYPE_KEYS:
        text = str(_first(header, key) or "").strip()
        for kind, pattern in _PATTERNS:
            if text and pattern.search(text):
                return f"{key} = '{text}' is a {kind}"
    for kind, pattern in _PATTERNS:
        if pattern.search(Path(filename).name):
            return f"the file name says {kind}"
    if _float(_first(header, "EXPTIME", "EXPOSURE")) == 0:
        return "no exposure time: a bias"
    return "nothing names a type: a light"


def read_frame(path: Path) -> Frame:
    with fits.open(readable(path), memmap=True) as hdul:
        i = find_image_hdu(hdul)
        hdu = hdul[i]
        h = inherited(hdul, i)  # the frame type of a multi-extension raw frame (HARPS) is in the primary header
        shape = tuple(int(n) for n in hdu.shape[-2:])
        cube = len(hdu.shape) > 2
    if cube:  # colour cubes and one-plane cubes: calibrated as their 2-D image (a copy in fits_from_raw)
        from ..io.bayer import fits_copy

        return read_frame(fits_copy(path))
    mode = h.get("READOUTM", h.get("READMODE"))  # the same setting under two names (MaxIm writes both to lights)
    settings = {"GAIN": h.get("GAIN"), "EGAIN": h.get("EGAIN"), "OFFSET": h.get("OFFSET"), "MODE": mode}
    readout = "|".join(f"{k}={v}" for k, v in settings.items() if v is not None)
    filt = _first(h, "FILTER", "FILTER1", "FILTNAME", "FILTERS", "HIERARCH ESO INS FILT1 NAME")
    # the disperser of a spectrograph belongs to the setting: a flat taken with another grism must not be used
    disperser = _first(
        h,
        "GRISM",
        "GRATING",
        "DISPERSR",
        "HIERARCH ESO INS GRIS1 NAME",
        "HIERARCH ESO INS GRAT1 NAME",
        "HIERARCH ESO INS GRAT NAME",
    )
    if disperser is not None and str(disperser).strip().lower() not in ("", "free", "none", "open"):
        filt = f"{str(filt).strip()} / {str(disperser).strip()}" if filt is not None else str(disperser).strip()
    ccdsum = str(h.get("CCDSUM", "")).split()  # '2 2' (NOAO, LCO)
    return Frame(
        path=str(path),
        kind=classify(h, str(path)),
        exptime=_float(_first(h, "EXPTIME", "EXPOSURE", "EXP_TIME")),
        filter=str(filt).strip() if filt is not None else None,
        temperature=_float(_first(h, "CCD-TEMP", "CCD_TEMP", "SENSOR-T", "DET-TEMP", "SET-TEMP")),
        binning=(
            int(
                _float(_first(h, "XBINNING", "BINX", "CCDXBIN", "HIERARCH ESO DET WIN1 BINX"))
                or (_float(ccdsum[0]) if len(ccdsum) == 2 else None)
                or 1
            ),
            int(
                _float(_first(h, "YBINNING", "BINY", "CCDYBIN", "HIERARCH ESO DET WIN1 BINY"))
                or (_float(ccdsum[1]) if len(ccdsum) == 2 else None)
                or 1
            ),
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
