"""Advice for the next night (plans/photometry.md PHO-43): what the measured night says about observing better.

Each item is a dict with a "kind" and the numbers behind it; the window words it. Kinds:
- "exposure": the exposure that brings the brightest measured star's highest peak to 60 % of the linearity limit
  (peaks above the sky scale with the exposure);
- "defocus": the brightest pixel holds more than 15 % of a star's light, so flat-field errors and pixel-to-pixel
  sensitivity weigh on every measurement; spreading the light lowers that term;
- "lost": stars missing on some frames (off the frame or not found), with the share of frames;
- "cadence": fewer than 10 points over the event's ingress at the night's cadence.
"""

import numpy as np

PEAK_TARGET = 0.6
PEAK_FRACTION = 0.15


def next_night(lc, exptime=None, linearity=None, ingress_days=None):
    out = []
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
