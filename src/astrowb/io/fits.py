"""FITS reading/writing on top of astropy.io.fits."""

from pathlib import Path

import numpy as np
from astropy.io import fits


def find_image_hdu(hdul) -> int:
    """Index of the first HDU holding an image of at least 2 dimensions."""
    for i, hdu in enumerate(hdul):
        # header only: touching .data would load (or refuse to memory-map) scaled integer data
        if isinstance(hdu, (fits.PrimaryHDU, fits.ImageHDU, fits.CompImageHDU)) and hdu.header.get("NAXIS", 0) >= 2:
            return i
    raise ValueError("no image data in file")


def plane(data) -> np.ndarray:
    """The 2-D image of a FITS data array: itself, the first plane of a cube, or the brightness
    (0.2126 R + 0.7152 G + 0.0722 B) of a colour cube with 3 or 4 planes (as some capture programs save)."""
    a = np.asarray(data)
    while a.ndim > 3:
        a = a[0]
    if a.ndim == 3:
        if a.shape[0] in (3, 4):
            p = a[:3].astype(np.float32)
            return p[0] * np.float32(0.2126) + p[1] * np.float32(0.7152) + p[2] * np.float32(0.0722)
        return a[0]
    return a


def read_image(path: Path):
    """Return (data, header, hdu_index). data is the first 2-D plane as float32; header is that HDU's header."""
    with fits.open(path, memmap=False) as hdul:
        i = find_image_hdu(hdul)
        data, header = hdul[i].data, hdul[i].header.copy()
    return np.asarray(plane(data), dtype=np.float32), header, i


def thumbnail(path, size=64):
    """A small screen picture (uint8, row 0 at the bottom as in FITS) of a file's first image, read with a pixel
    step (only those rows from the disk), so a list of hundreds of large files is drawn quickly. Works for
    16-bit camera files with BZERO, which cannot be memory-mapped."""
    from ..display import to_display

    with fits.open(path, memmap=False, lazy_load_hdus=True) as hdul:
        hdu = hdul[find_image_hdu(hdul)]
        h = hdu.header
        step = max(1, -(-max(h["NAXIS1"], h["NAXIS2"]) // size))  # at most `size` pixels across
        index = (0,) * (int(h["NAXIS"]) - 2) + (slice(None, None, step), slice(None, None, step))
        small = np.array(hdu.section[index], dtype=np.float32)
    return to_display(small)


def image_hdus(path):
    """[(index, label)] of every HDU holding an image (multi-extension files: mosaics, HST/JWST products...)."""
    out = []
    with fits.open(path, memmap=False) as hdul:
        for i, hdu in enumerate(hdul):
            h = hdu.header
            if isinstance(hdu, (fits.PrimaryHDU, fits.ImageHDU, fits.CompImageHDU)) and h.get("NAXIS", 0) >= 2:
                shape = " x ".join(str(h.get(f"NAXIS{k}")) for k in range(1, h["NAXIS"] + 1))
                out.append((i, f"{i}: {h.get('EXTNAME', 'PRIMARY' if i == 0 else 'image')} ({shape})"))
    return out


def extract_extension(path, index):
    """The image of HDU `index` as a file of its own next to the original (<name>_<EXTNAME or extN>_<index>.fits),
    so every tool (header editing, processing, plate solving, photometry) works on what is shown; the primary
    header's keywords (telescope, time, filter...) are kept where the extension does not set them. The original
    is not touched; a copy made earlier from the unchanged original is reused."""
    import re

    path = Path(path)
    with fits.open(path, memmap=False) as hdul:
        hdu = hdul[index]
        name = re.sub(r"[^A-Za-z0-9_-]+", "_", str(hdu.header.get("EXTNAME", "ext"))) or "ext"
        dest = path.with_name(f"{path.stem}_{name}_{index}.fits")
        if dest.exists() and dest.stat().st_mtime >= path.stat().st_mtime:
            return dest
        header = hdu.header.copy()
        for card in hdul[0].header.cards if index else []:
            skip = STRUCTURAL + ("COMMENT", "HISTORY", "")
            if card.keyword not in skip and card.keyword not in header:
                header[card.keyword] = (card.value, card.comment)
        for key in ("XTENSION", "PCOUNT", "GCOUNT", "EXTNAME", "EXTVER"):
            header.remove(key, ignore_missing=True)
        header.add_history(f"extension {index} of {path.name}")
        fits.PrimaryHDU(hdu.data, header).writeto(dest, overwrite=True, output_verify="silentfix")
    return dest


STRUCTURAL = ("SIMPLE", "BITPIX", "NAXIS", "EXTEND", "BZERO", "BSCALE", "PCOUNT", "GCOUNT", "XTENSION", "END")


def parse_value(text: str):
    """A header value typed by a user: T / F, an integer, a float, else the text itself."""
    t = text.strip()
    if t in ("T", "F"):
        return t == "T"
    for kind in (int, float):
        try:
            return kind(t)
        except ValueError:
            pass
    return t


def save_as(
    source: Path, destination: Path, history: str | None = None, overwrite: bool = False, set_cards=None, delete=()
) -> Path:
    """Write a copy of every HDU in source to destination, optionally adding a HISTORY card, setting keywords
    ({key: [value, comment]}) and deleting keywords in the image HDU's header. The data are not touched."""
    if Path(source).resolve() == Path(destination).resolve():
        raise ValueError("destination must differ from source")
    for key in [*(set_cards or {}), *delete]:
        if key.upper().rstrip("0123456789") in STRUCTURAL:
            raise ValueError(f"the keyword {key.upper()} describes the data and cannot be edited")
    for key, (value, comment) in (set_cards or {}).items():
        if not all(str(t).isascii() for t in (key, value, comment or "")):
            raise ValueError(f"the value of {key.upper()} must be plain ASCII text (FITS standard)")
    with fits.open(source, memmap=False) as hdul:
        header = hdul[find_image_hdu(hdul)].header
        for key in delete:
            header.remove(key.upper(), ignore_missing=True, remove_all=True)
        for key, (value, comment) in (set_cards or {}).items():
            header[key.upper()] = (value, comment or None)
        if history:
            header.add_history(history)
        hdul.writeto(destination, overwrite=overwrite, output_verify="silentfix")
    return Path(destination)
