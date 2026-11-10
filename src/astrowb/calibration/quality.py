"""Is the calibration good? Numbers for every master (plans/calibration.md CAL-6; the quality parameters LCO's BANZAI
and ESO's pipelines keep, in an observer's words):

    level_noise(master, n_inputs, single_noise)   level, noise against σ_single/√N, the excess (pattern)
    banding(master)                               RMS of the row and column medians about a smooth trend (ADU)
    hot_pixels(dark)                              pixels far above the dark's level (count and places)
    dark_current(dark, bias, exptime, gain)       e⁻ per pixel per second
    flat_levels(flat_medians, full_well)          each input flat's level as a share of full well; 20–80 % advised
    dust(flat)                                    dark rings and spots: their places and depths (share of the level)
    flat_noise(flat, n_inputs, level, gain)       the noise the master flat adds per pixel, and over an aperture
    report(kind, master, …)                       all that applies to that kind, with green / amber marks
"""

import numpy as np
from scipy import ndimage


def _robust_sigma(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return float(1.4826 * np.median(np.abs(x - np.median(x))))


def level_noise(master, n_inputs=None, single_noise=None):
    """{"level", "noise", "expected", "excess"}: the master's median and robust pixel scatter; expected =
    single_noise / √n_inputs when both are known; excess = √(noise² − expected²) (pattern, not averaged away)."""
    m = np.asarray(master)
    out = {"level": float(np.nanmedian(m[::2, ::2])), "noise": _robust_sigma(m[::2, ::2])}
    if n_inputs and single_noise:
        out["expected"] = float(single_noise / np.sqrt(n_inputs))
        out["excess"] = float(np.sqrt(max(out["noise"] ** 2 - out["expected"] ** 2, 0.0)))
    return out


def banding(master, smooth=31):
    """{"rows", "columns"}: the RMS (ADU) of the row and column medians about their running median — a pattern of
    lines; a smooth gradient is no banding."""
    m = np.asarray(master)
    out = {}
    for name, axis in (("rows", 1), ("columns", 0)):
        k = max(1, m.shape[axis] // 1024)  # a large master: every k-th pixel along, ~1000 per median
        prof = np.nanmedian(m[:, ::k] if axis == 1 else m[::k, :], axis=axis)
        trend = ndimage.median_filter(prof, size=min(smooth, len(prof) // 2 * 2 + 1), mode="nearest")
        out[name] = _robust_sigma(prof - trend)
    return out


def hot_pixels(dark, nsigma=10.0):
    """{"count", "places" (y, x of the first 1000), "threshold"}: pixels above the level by nsigma robust σ."""
    d = np.asarray(dark)
    level, sigma = float(np.nanmedian(d[::2, ::2])), _robust_sigma(d[::2, ::2])
    hot = d > level + nsigma * max(sigma, 1e-9)
    ys, xs = np.nonzero(hot)
    return {"count": int(hot.sum()), "places": list(zip(ys[:1000].tolist(), xs[:1000].tolist(), strict=True)),
            "threshold": level + nsigma * sigma}  # fmt: skip


def amp_glow(dark, corner=0.1):
    """{"excess" (ADU), "significance", "glow"}: the brightest corner of a master dark against its centre (CAL-3;
    the amplifier glow of CMOS sensors, which does not grow in proportion to the exposure)."""
    d = np.asarray(dark)
    ny, nx = d.shape
    cy, cx = max(4, int(ny * corner)), max(4, int(nx * corner))
    centre = d[ny // 2 - cy // 2 : ny // 2 + cy // 2, nx // 2 - cx // 2 : nx // 2 + cx // 2]
    corners = (d[:cy, :cx], d[:cy, -cx:], d[-cy:, :cx], d[-cy:, -cx:])
    level = float(np.nanmedian(centre))
    excess = max(float(np.nanmedian(c)) for c in corners) - level
    noise = _robust_sigma(centre) / np.sqrt(cy * cx)
    significance = excess / max(noise, 1e-9)
    return {"excess": excess, "significance": float(significance), "glow": bool(significance > 10 and excess > 2.0)}


def dark_current(dark, bias, exptime, gain=1.0):
    """e⁻ per pixel per second: the dark's median above the bias's, times the gain, over the exposure."""
    return float((np.nanmedian(np.asarray(dark, float)) - np.nanmedian(np.asarray(bias, float))) * gain / exptime)


def flat_levels(medians, full_well):
    """[{"level", "share", "ok"}] per input flat: its median as a share of full well (20–80 % advised: below, the
    flat is noisy; above, the camera is no longer linear)."""
    return [{"level": float(m), "share": float(m / full_well), "ok": bool(0.2 <= m / full_well <= 0.8)}
            for m in medians]  # fmt: skip


def dust(flat, smooth=51, min_depth=0.01, min_size=3, binning=None):
    """[{"x", "y", "depth", "radius"}] of dust shadows: the flat over its large-scale shape, smoothed, and the
    connected regions darker than min_depth (deepest first). A large flat is searched binned (motes span tens of
    pixels); places and radii are given in the flat's own pixels."""
    flat = np.asarray(flat, float)
    k = binning or max(1, int(np.ceil(max(flat.shape) / 1024)))
    if k > 1:
        ny, nx = flat.shape[0] // k * k, flat.shape[1] // k * k
        f = flat[:ny, :nx].reshape(ny // k, k, nx // k, k).mean(axis=(1, 3))
        found = dust(f, smooth, min_depth, max(2, min_size // k + 1), binning=1)  # the same window: motes are big
        return [d | {"x": d["x"] * k + (k - 1) / 2, "y": d["y"] * k + (k - 1) / 2, "radius": d["radius"] * k}
                for d in found]  # fmt: skip
    f = flat
    big = ndimage.median_filter(f[::4, ::4], size=max(3, smooth // 4), mode="nearest")
    big = ndimage.zoom(big, (f.shape[0] / big.shape[0], f.shape[1] / big.shape[1]), order=1)[: f.shape[0], : f.shape[1]]
    raw = f / big - 1.0
    ratio = ndimage.gaussian_filter(raw, 1.5)  # found on the smoothed ratio, measured on the nearly raw one
    fine = ndimage.median_filter(raw, size=3)
    labels, n = ndimage.label(ratio < -min_depth)
    edge = max(4, smooth // 6)  # the large-scale shape is least sure at the borders
    out = []
    for k, sl in enumerate(ndimage.find_objects(labels), start=1):
        region = labels[sl] == k
        touches = (
            sl[0].start < edge or sl[1].start < edge or sl[0].stop > f.shape[0] - edge or sl[1].stop > f.shape[1] - edge
        )
        if region.sum() < min_size**2 or touches:
            continue
        depth = -float(fine[sl][region].min())
        cy, cx = ndimage.center_of_mass(region)
        out.append({"x": float(sl[1].start + cx), "y": float(sl[0].start + cy), "depth": depth,
                    "radius": float(np.sqrt(region.sum() / np.pi))})  # fmt: skip
    return sorted(out, key=lambda d: -d["depth"])


def flat_noise(flat, n_inputs, level_adu, gain=1.0, aperture_px=80):
    """{"per_pixel", "aperture"}: the relative noise the master flat adds — the photon noise of n_inputs flats of
    level_adu, averaged — per pixel and over an aperture of aperture_px pixels."""
    per_pixel = 1.0 / np.sqrt(n_inputs * level_adu * gain)
    return {"per_pixel": float(per_pixel), "aperture": float(per_pixel / np.sqrt(aperture_px))}


def report(kind, master, **known):
    """The checks that apply to a master of this kind ("bias", "dark", "flat"): {check: {"value", "ok", "note"}}.
    known: n_inputs, single_noise, bias (a master), exptime, gain, input_medians, full_well."""
    out = {}
    ln = level_noise(master, known.get("n_inputs"), known.get("single_noise"))
    out["level"] = {"value": ln["level"], "ok": True, "note": "median"}
    if "excess" in ln:
        ok = ln["excess"] <= 0.5 * ln["expected"]
        out["excess_noise"] = {"value": ln["excess"], "ok": ok, "note": "noise beyond σ/√N (pattern)"}
    band = banding(master)
    worst = max(band.values())
    out["banding"] = {
        "value": worst,
        "ok": worst <= 0.5 * max(ln["noise"], 1e-9),
        "note": "RMS of row / column medians",
    }
    if kind == "dark":
        glow = amp_glow(master)
        out["amp_glow"] = {"value": glow["excess"], "ok": not glow["glow"], "note": "corner above centre (ADU)"}
        hot = hot_pixels(master)
        out["hot_pixels"] = {"value": hot["count"], "ok": hot["count"] < 1e-3 * np.size(master), "note": "≥ 10σ"}
        if known.get("bias") is not None and known.get("exptime"):
            dc = dark_current(master, known["bias"], known["exptime"], known.get("gain", 1.0))
            out["dark_current"] = {"value": dc, "ok": True, "note": "e⁻/px/s"}
    if kind == "flat":
        if known.get("input_medians") is not None and known.get("full_well"):
            levels = flat_levels(known["input_medians"], known["full_well"])
            out["flat_levels"] = {"value": max(x["share"] for x in levels), "ok": all(x["ok"] for x in levels),
                                  "note": "highest input flat as a share of full well (20–80 %)"}  # fmt: skip
        motes = dust(master / np.nanmedian(master))
        out["dust"] = {"value": motes[0]["depth"] if motes else 0.0, "ok": not motes or motes[0]["depth"] < 0.05,
                       "note": f"{len(motes)} shadows; the deepest's depth"}  # fmt: skip
    return out
