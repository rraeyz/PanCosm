"""The variance and quality planes of a calibrated light (plans/calibration.md CAL-13): `core/planes` carries the
variance through the same bias, dark and flat that `masters.calibrate` applied, and the file is written as
SCI / VAR / DQ extensions (or as a plain FITS when Settings → Files says so)."""

import numpy as np

from ..core import planes
from ..hdr import get
from . import masters


def camera(header, params):
    """(gain e⁻/ADU, read noise e⁻, saturation ADU or None): the header first, then the run's own numbers."""
    gain = get(header, "EGAIN", "GAIN", default=0.0) or params.get("gain") or 0.0
    rn = get(header, "RDNOISE", "READNOIS", "READNOISE", default=0.0) or params.get("read_noise") or 0.0
    sat = get(header, "SATURATE", "DATAMAX", default=0.0) or params.get("saturation") or None
    return float(gain), float(rn), sat


def frame(data, light, header, exptime, params, used, k=1.0, defects=None):
    """The calibrated `data` as a planes.Frame. used: {"bias"|"dark"|"flat": (master, header, variance or None)}.
    Without a gain there is no variance (only DQ) and the header says so; a master without a variance counts 0."""
    gain, rn, sat = camera(header, params)
    b, d, f = (used.get(n, (None, None, None)) for n in ("bias", "dark", "flat"))
    raw = planes.Frame.from_raw(light, gain or 1.0, rn, sat, bias_level=0.0 if b[0] is None else np.median(b[0]))
    dq = raw.dq
    if defects is not None:
        dq[defects] |= planes.BAD | planes.REPAIRED
    note = []
    if gain:
        with np.errstate(all="ignore"):
            out = planes.calibrate(raw, *_as_frames(b, d, f, exptime, note), k=k, flat=_flat(f, note))
        var, dq = out.var, dq | out.dq
    else:
        var = None
        note.append("no gain known: variance plane not written")
    dq[~np.isfinite(data)] |= planes.BAD
    header = header.copy()
    for text in note:
        header.add_history(f"planes: {text}")
    return planes.Frame(data, var, dq, header)


def _frame(sci, var, scale=1.0):
    return None if sci is None else planes.Frame(sci, scale**2 * (0 * sci if var is None else var), None)


def _as_frames(b, d, f, exptime, note):
    """bias and dark as Frames the way masters.calibrate subtracts them (the dark scaled to the exposure)."""
    bias = _frame(b[0], b[2])
    dark = None
    if d[0] is not None:
        signal = masters.dark_for(exptime, b[0], d[0], d[1])
        if signal is not None:
            t = d[1].get("EXPTIME", 0.0) or 0.0
            dark = _frame(signal, d[2], exptime / t if d[1].get("BIASSUB") and t > 0 else 1.0)
    for name, m in (("bias", b), ("dark", d), ("flat", f)):
        if m[0] is not None and m[2] is None:
            note.append(f"master {name} has no variance: counted as 0")
    return bias, dark


def _flat(f, note):
    return _frame(f[0], f[2])


def used_masters(entry, built, variances, flat_used):
    """{"bias"|"dark"|"flat": (data, header, variance)} of the masters this light was calibrated with."""
    return {k: (*built[entry[k]][:2], variances.get(entry[k])) for k in ("bias", "dark", "flat")
            if entry[k] and (k != "flat" or flat_used)}  # fmt: skip


def save(path, data, header, params, light=None, exptime=0.0, used=None, k=1.0, defects=None, cosmic=None):
    """Write one calibrated light: SCI / VAR / DQ extensions, or a plain FITS when `light` is None (colour frames
    are split: the planes would need the same split) or Settings → Files turned the planes off."""
    if light is None or not params.get("write_planes", True):
        header.add_history("planes: not written (" + ("setting is off" if light is not None else "colour split") + ")")
        return masters.save(path, data, header)
    fr = frame(data, light, header, exptime, params, used or {}, k, defects)
    if cosmic is not None:
        fr.dq[cosmic] |= planes.COSMIC | planes.REPAIRED
    return str(planes.write(path, fr))


def save_master(path, data, header, var=None):
    """A master as plain FITS, or with its variance (SCI + VAR, the layout of the calibrated lights) when given."""
    if var is None:
        return masters.save(path, data, header)
    return str(planes.write(path, planes.Frame(np.asarray(data, np.float32), var, None, header)))
