"""Advice for the next night (plans/photometry.md PHO-43): what the measured night says about observing better.

Each item is a dict with a "kind" and the numbers behind it; the window words it. Kinds:
- "exposure": the exposure that brings the brightest measured star's highest peak to 60 % of the linearity limit
  (peaks above the sky scale with the exposure);
- "defocus": the brightest pixel holds more than 15 % of a star's light, so flat-field errors and pixel-to-pixel
  sensitivity weigh on every measurement; spreading the light lowers that term;
- "lost": stars missing on some frames (off the frame or not found), with the share of frames;
- "cadence": fewer than 10 points over the event's ingress at the night's cadence;
- "noise": the largest term of the target's noise budget (photon, sky, scintillation; errors.budget) when it is not
  the photon noise, with its share of the variance;
- "drift": the target moved more than DRIFT_PX over the night: the flat field's pixel-to-pixel and large-scale
  errors then enter the light curve (better guiding, or flats of the same night);
- "pointing": stars lost or within the sky ring of the edge: the shift of the pointing (dx, dy in pixels, + to the
  right and up on the frame) that centres every star's path over the night, when the field fits.
"""

import numpy as np

PEAK_TARGET = 0.6
PEAK_FRACTION = 0.15
DRIFT_PX = 5.0


def next_night(lc, exptime=None, linearity=None, ingress_days=None, gain=1.0, shape=None):
    out = _noise(lc, gain) + _pointing(lc, shape) + _drift(lc)
    peak = np.asarray(lc.get("peak") or [], float)
    sky = np.asarray(lc.get("sky") or [], float)
    limit = linearity or lc.get("saturation")
    if exptime and limit and peak.ndim == 2 and peak.size:
        n = min(peak.shape[1], sky.shape[1]) if sky.ndim == 2 else peak.shape[1]
        above = peak[:, :n] - (sky[:, :n] if sky.ndim == 2 else 0.0)
        star = int(np.nanargmax(np.nanmax(above, axis=0)))
        top, background = float(np.nanmax(above[:, star])), float(np.nanmedian(peak[:, star] - above[:, star]))
        if top > 0:
            t = exptime * (PEAK_TARGET * limit - background) / top
            if t > 0 and abs(t / exptime - 1) > 0.2:
                out.append({"kind": "exposure", "now": float(exptime), "suggest": round(float(t), 1), "star": star,
                            "peak": top + background, "limit": float(limit)})  # fmt: skip
    flux = np.asarray(lc.get("target_flux") or [], float)
    if peak.ndim == 2 and peak.size and flux.size:
        above = peak[:, 0] - (sky[:, 0] if sky.ndim == 2 else 0.0)
        share = float(np.nanmedian(above / flux))
        if np.isfinite(share) and share > PEAK_FRACTION:
            out.append({"kind": "defocus", "share": round(share, 3)})
    frames = len(lc.get("time") or [])
    lost = {}
    for why in (lc.get("lost") or {}).values():
        if why and why[0] == "comparison" and len(why) > 1:
            lost[int(why[1])] = lost.get(int(why[1]), 0) + 1
    for ks in (lc.get("partial") or {}).values():
        for k in ks:
            lost[int(k)] = lost.get(int(k), 0) + 1
    if frames:
        out += [{"kind": "lost", "star": k, "share": round(c / frames, 3)} for k, c in sorted(lost.items())]
    t = np.asarray(lc.get("time") or [], float)
    if ingress_days and t.size > 2:
        cadence = float(np.median(np.diff(t)))
        if cadence > 0 and ingress_days / cadence < 10:
            out.append({"kind": "cadence", "points": round(ingress_days / cadence, 1), "cadence_s": cadence * 86400})
    return out


def _noise(lc, gain):
    from .errors import budget

    flux, sky = np.asarray(lc.get("target_flux") or [], float), np.asarray(lc.get("sky") or [], float)
    radii = lc.get("radii") or []
    if not flux.size or sky.ndim != 2 or not radii:
        return []
    scint = np.nanmedian(lc["scintillation"]) if lc.get("scintillation") else 0.0
    pixels = np.pi * float(np.median([r[0] for r in radii])) ** 2
    parts, _ = budget(np.nanmedian(flux) * gain, np.nanmedian(sky[:, 0]) * gain, 0.0, 0.0, pixels, scint)
    worst = max(parts, key=parts.get)
    share = parts[worst] / sum(parts.values())
    return [] if worst == "photon" else [{"kind": "noise", "term": worst, "share": round(float(share), 3)}]


def _pointing(lc, shape):
    xy = np.asarray(lc.get("xy") or [], float)
    if shape is None or xy.ndim != 3 or not xy.size:
        return []
    ny, nx = shape
    margin = float(np.median([r[2] for r in lc["radii"]])) if lc.get("radii") else 15.0
    lo, hi = np.nanmin(xy, axis=(0, 1)), np.nanmax(xy, axis=(0, 1))
    near = (lo < margin).any() or (hi > np.array([nx - 1, ny - 1]) - margin).any()
    if not (near or lc.get("lost") or lc.get("partial")):
        return []
    span = hi - lo
    if (span + 2 * margin > np.array([nx, ny])).any():
        return [{"kind": "pointing", "fits": False}]
    dx, dy = np.array([nx - 1, ny - 1]) / 2 - (lo + hi) / 2
    if max(abs(dx), abs(dy)) < 0.05 * min(nx, ny):
        return []
    return [{"kind": "pointing", "fits": True, "dx": round(float(dx)), "dy": round(float(dy))}]


def _drift(lc):
    xy = np.asarray(lc.get("xy") or [], float)
    if xy.ndim != 3 or not xy.size:
        return []
    path = xy[:, 0, :]
    moved = float(np.nanmax(np.hypot(*(path - np.nanmedian(path, axis=0)).T)) * 2)
    return [{"kind": "drift", "px": round(moved, 1)}] if moved > DRIFT_PX else []
