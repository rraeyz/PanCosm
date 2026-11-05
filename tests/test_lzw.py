"""Unix compress (.Z) files, as the ESO archive delivers raw frames: decoded here without an extra package."""

import numpy as np
import pytest
from astropy.io import fits

from astrowb.io.lzw import readable, unlzw


def _lzw(data: bytes, max_bits=16):
    """A minimal compress-format writer for the test (block mode), so the test runs everywhere."""
    table = {bytes([i]): i for i in range(256)}
    next_code, bits, out_codes = 257, 9, []
    w = b""
    widths = []
    for c in data:
        wc = w + bytes([c])
        if wc in table:
            w = wc
            continue
        out_codes.append(table[w])
        widths.append(bits)
        if next_code < (1 << max_bits):
            table[wc] = next_code
            next_code += 1
            if next_code > (1 << bits) and bits < max_bits:
                bits += 1
        w = bytes([c])
    if w:
        out_codes.append(table[w])
        widths.append(bits)
    # pack in groups: when the width changes, the previous group of eight codes is padded (compress's layout)
    out, buf, nbits, group_start, prev_width = bytearray(), 0, 0, 0, widths[0] if widths else 9
    for code, width in zip(out_codes, widths, strict=True):
        if width != prev_width:
            if nbits:
                out.append(buf & 0xFF)
                buf, nbits = 0, 0
            used = len(out) - group_start
            if used % prev_width:
                out += bytes(prev_width - used % prev_width)
            group_start, prev_width = len(out), width
        buf |= code << nbits
        nbits += width
        while nbits >= 8:
            out.append(buf & 0xFF)
            buf >>= 8
            nbits -= 8
    if nbits:
        out.append(buf & 0xFF)
    return bytes([0x1F, 0x9D, 0x80 | max_bits]) + bytes(out)


def test_round_trip_through_the_code_size_changes():
    rng = np.random.default_rng(1)
    data = bytes(rng.integers(0, 40, 300000, dtype=np.uint8)) + b"abcabcabc" * 2000  # codes up to 16 bits
    assert unlzw(_lzw(data)) == data
    with pytest.raises(ValueError):
        unlzw(b"not compressed")


def test_a_fits_frame_in_z_is_read_everywhere(tmp_path):
    img = np.arange(120 * 80, dtype=np.int16).reshape(80, 120)
    fits.PrimaryHDU(img, fits.Header({"DATE-OBS": "2019-01-01T07:49:08", "EXPTIME": 80.0})).writeto(tmp_path / "a.fits")
    raw = (tmp_path / "a.fits").read_bytes()
    (tmp_path / "EFOSC.2019-01-01T07_49_08.fits.Z").write_bytes(_lzw(raw))
    (tmp_path / "a.fits").unlink()
    from astrowb.calibration.masters import load
    from astrowb.io.bayer import fits_copy
    from astrowb.io.fits import read_image

    z = tmp_path / "EFOSC.2019-01-01T07_49_08.fits.Z"
    assert readable(z).parent.name == "fits_from_raw" and readable(z).read_bytes() == raw
    assert np.array_equal(read_image(z)[0], img) and np.array_equal(load(z)[0], img)
    assert fits_copy(z).name == "EFOSC.2019-01-01T07_49_08.fits"
