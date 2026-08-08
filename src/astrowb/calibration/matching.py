"""Automatic matching of calibration frames to lights, and the calibration plan.

Rules (MaxIm DL "auto-calibration" style, made explicit):
  every match: same frame size, binning and readout settings (gain/offset/mode); for flats the read-out mode
         only: the flat's pixel pattern does not depend on the gain (normalised away) nor the offset (the bias)
  bias:  nearest sensor temperature
  dark:  temperature within ``temp_tol``; same exposure preferred, otherwise the
         bias-subtracted dark with the nearest exposure (scaled)
  flat:  same filter; nearest in time
A missing match is not an error: the plan lists it so the user can add frames or
continue without that correction.
"""

import math
from collections import defaultdict
from dataclasses import dataclass, field

from .frames import Frame

TEMP_TOL = 2.0  # deg C


def _settings_agree(a: str, b: str, keys=None) -> bool:
    """Gain, offset and read-out mode (or only keys) agree where both headers state them: a setting one program
    does not write is no conflict (the real night's lights had READMODE, its bias, darks and flats did not)."""
    da, db = (dict(part.split("=", 1) for part in s.split("|") if part) for s in (a, b))
    return all(da[k] == db[k] for k in da.keys() & db.keys() if keys is None or k in keys)


def _compatible(a: Frame, b: Frame, keys=None) -> bool:
    return a.shape == b.shape and a.binning == b.binning and _settings_agree(a.readout, b.readout, keys)


def _temp_diff(a, b):
    return abs(a.temperature - b.temperature) if a.temperature is not None and b.temperature is not None else 0.0


def _same_exp(a, b):
    return a is not None and b is not None and abs(a - b) <= 0.01 * max(a, b, 1e-9)


def _norm_filter(f):
    return (f or "").strip().lower()


def group_key(frame: Frame) -> tuple:
    """Frames with the same key are combined into one master."""
    base = (frame.kind, frame.shape, frame.binning, frame.readout)
    if frame.kind == "dark":
        return base + (round(frame.exptime or 0, 3), None if frame.temperature is None else round(frame.temperature))
    if frame.kind == "flat":
        return base + (_norm_filter(frame.filter),)
    return base


def best_bias(light, biases):
    ok = [b for b in biases if _compatible(light, b)]
    return min(ok, key=lambda b: _temp_diff(light, b), default=None)


def best_dark(light, darks, temp_tol=TEMP_TOL, can_scale=lambda d: True):
    ok = [d for d in darks if _compatible(light, d) and _temp_diff(light, d) <= temp_tol]
    exact = [d for d in ok if _same_exp(light.exptime, d.exptime)]
    if exact:
        return min(exact, key=lambda d: _temp_diff(light, d))
    scalable = [d for d in ok if can_scale(d) and d.exptime and light.exptime]
    return min(scalable, key=lambda d: (abs(math.log(light.exptime / d.exptime)), _temp_diff(light, d)), default=None)


def best_flat(light, flats):
    # a pipeline's master flat states another GAIN (BANZAI: 17291 against the lights' 0.78): the mode only
    ok = [f for f in flats if _compatible(light, f, ("MODE",)) and _norm_filter(f.filter) == _norm_filter(light.filter)]
    return min(ok, key=lambda f: abs(_time(f) - _time(light)), default=None)


def _time(frame):
    from astropy.time import Time

    try:
        return Time(frame.date_obs).jd if frame.date_obs else 0.0
    except ValueError:
        return 0.0


@dataclass
class Plan:
    groups: dict = field(default_factory=dict)  # group key -> list of paths (masters to build)
    lights: list = field(
        default_factory=list
    )  # [{"light": path, "bias": key|None, "dark": key|None, "flat": key|None}]
    missing: list = field(default_factory=list)  # [(light path, "bias"|"dark"|"flat", what it must match)]
    unknown: list = field(default_factory=list)  # paths that could not be classified


def make_plan(frames: list[Frame], temp_tol=TEMP_TOL) -> Plan:
    plan = Plan()
    groups = defaultdict(list)
    for f in frames:
        if f.kind == "unknown":
            plan.unknown.append(f.path)
        elif f.kind not in ("light", "arc"):  # masters are made of bias, darks and flats only
            groups[group_key(f)].append(f)
    plan.groups = {k: [f.path for f in v] for k, v in groups.items()}
    by_kind = defaultdict(list)
    for members in groups.values():
        by_kind[members[0].kind].append(members[0])  # representative frame of each group
    have_bias = bool(by_kind["bias"])
    for light in (f for f in frames if f.kind in ("light", "arc")):
        entry = {"light": light.path}
        b = best_bias(light, by_kind["bias"])
        d = best_dark(light, by_kind["dark"], temp_tol, can_scale=lambda _: have_bias)
        f = best_flat(light, by_kind["flat"]) if light.kind == "light" else None  # a lamp is never flat-fielded
        entry["flat"] = None
        for kind, match in (("bias", b), ("dark", d)) + ((("flat", f),) if light.kind == "light" else ()):
            entry[kind] = group_key(match) if match else None
            if match is None and light.kind == "light":  # a lamp's line positions do not need its dark
                plan.missing.append((light.path, kind, _why(light, temp_tol)))
        plan.lights.append(entry)
    return plan


def _why(light, temp_tol):
    """What the missing frame would have to match (the UI turns this into a translated sentence)."""
    return {
        "filter": light.filter,
        "shape": list(light.shape),
        "binning": list(light.binning),
        "exptime": light.exptime,
        "temperature": light.temperature,
        "temp_tol": temp_tol,
    }
