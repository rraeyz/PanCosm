"""Unix `compress` (.Z, LZW) files, as the ESO archive and older observatories deliver raw FITS frames.

astropy reads them only with an extra package; this is the decoder written from the format's description (the
algorithm Mark Adler documents in pigz's unlzw: 9 to 16-bit codes, block mode with a clear code 256, and codes read
in groups of eight so that the input is realigned whenever the code size changes or the table is cleared).
"""

from pathlib import Path


def unlzw(data: bytes) -> bytes:
    """The decompressed bytes of a .Z file."""
    if len(data) < 3 or data[0] != 0x1F or data[1] != 0x9D:
        raise ValueError("not a .Z (compress) file: check the file name, or download it again")
    flags = data[2]
    max_bits = flags & 0x1F
    block = bool(flags & 0x80)
    if not 9 <= max_bits <= 16 or flags & 0x60:
        raise ValueError("unsupported .Z file: decompress it with gzip -d or 7-Zip and open the .fits")
    n = len(data)
    pos = mark = 3  # next byte to read; start of the current group of codes
    buf = left = 0  # bit buffer, least significant bits first
    bits, mask = 9, 0x1FF
    end = 256 if block else 255  # last code in the table
    table = [bytes((i,)) for i in range(256)] + [b""] * (65536 - 256)  # each code's whole string
    out = bytearray()
    if pos >= n:
        return bytes(out)

    def flush():  # skip to the end of the current group of eight codes
        nonlocal pos, mark, buf, left
        rem = (pos - mark) % bits
        if rem:
            pos += bits - rem
        buf = left = 0
        mark = pos

    while left < bits and pos < n:
        buf |= data[pos] << left
        pos += 1
        left += 8
    if left < bits:
        return bytes(out)
    prev = buf & mask
    buf >>= bits
    left -= bits
    if prev > 255:
        raise ValueError("damaged .Z file: download it again")
    out.append(prev)
    while True:
        if end >= mask and bits < max_bits:  # the table is full at this size: one more bit per code
            flush()
            bits += 1
            mask = (mask << 1) | 1
        while left < bits and pos < n:
            buf |= data[pos] << left
            pos += 1
            left += 8
        if left < bits:
            break  # end of the data
        code = buf & mask
        buf >>= bits
        left -= bits
        if code == 256 and block:  # clear: start again with 9-bit codes
            flush()
            bits, mask, end = 9, 0x1FF, 255
            continue
        if code > end:  # the code being defined now (KwKwK)
            if code != end + 1 or prev > end:
                raise ValueError("damaged .Z file: download it again")
            entry = table[prev] + table[prev][:1]
        else:
            entry = table[code]
        if end < mask:
            end += 1
            table[end] = table[prev] + entry[:1]
        prev = code
        out += entry
    return bytes(out)


def is_compress(path) -> bool:
    return str(path).lower().endswith(".z") and not str(path).lower().endswith(".gz")


def decompressed_copy(path, folder=None) -> Path:
    """The .Z file decompressed next to it (or in folder), once; the copy is reused afterwards."""
    path = Path(path)
    target = Path(folder or path.parent) / path.name[:-2]
    if not target.exists() or target.stat().st_mtime < path.stat().st_mtime:
        tmp = target.with_name(target.name + ".part")
        tmp.write_bytes(unlzw(path.read_bytes()))
        tmp.replace(target)  # never a half-written frame
    return target


def readable(path):
    """path itself, or for a compressed FITS frame (.fits.Z) its decompressed copy in fits_from_raw next to it."""
    path = Path(path)
    if not is_compress(path):
        return path
    folder = path.parent / "fits_from_raw"
    folder.mkdir(exist_ok=True)
    return decompressed_copy(path, folder)
