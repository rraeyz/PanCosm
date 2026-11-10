"""Frames read out by several amplifiers (plans/calibration.md CAL-4; IRAF mscred / ccdproc per amplifier): each
amplifier has its own overscan strip, bias level and gain. Every amplifier's part is corrected by its own overscan,
scaled to the first amplifier's gain (one unit for the whole frame) and put in its place on the detector.

    amps = layout(header)          [{"data", "bias", "det", "gain"}] from DATASECn / BIASSECn / DETSECn / GAINn
    image = join(raw, header)      the overscan-corrected, gain-matched, trimmed frame (None when one amplifier)
"""

import numpy as np

from .masters import overscan_level, section


def layout(header, max_amps=16):
    """The amplifiers the header describes (numbered keywords), or [] for a one-amplifier frame."""
    from ..hdr import get

    amps = []
    for n in range(1, max_amps + 1):
        data, bias = section(header.get(f"DATASEC{n}", "")), section(header.get(f"BIASSEC{n}", ""))
        if data is None or bias is None:
            continue
        det = section(header.get(f"DETSEC{n}", "")) or data
        amps.append({"n": n, "data": data, "bias": bias, "det": det,
                     "gain": float(get(header, f"GAIN{n}", "GAIN", default=1.0) or 1.0)})  # fmt: skip
    return amps if len(amps) > 1 else []


def join(raw, header, order=1):
    """The frame with each amplifier's overscan removed, scaled to the first amplifier's gain (ADU of amplifier 1)
    and placed by its DETSEC; None when the header names fewer than two amplifiers."""
    amps = layout(header)
    if not amps:
        return None
    raw = np.asarray(raw, np.float64)
    rows = [a["det"][0] for a in amps]
    cols = [a["det"][1] for a in amps]
    y0, x0 = min(r.start for r in rows), min(c.start for c in cols)
    ny, nx = max(r.stop for r in rows) - y0, max(c.stop for c in cols) - x0
    out = np.full((ny, nx), np.nan)
    g0 = amps[0]["gain"]
    for a in amps:
        level = overscan_level(raw[a["bias"]], a["bias"], a["data"], order=order)
        part = (raw[a["data"]] - level) * (a["gain"] / g0)
        r, c = a["det"]
        out[r.start - y0 : r.stop - y0, c.start - x0 : c.stop - x0] = part
    return out.astype(np.float32)
