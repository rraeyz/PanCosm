"""Comparison-star rules the user can set, with the reason for every star left out (plans/photometry.md PHO-17).

The rules gather Siril's findcompstars (brightness and colour windows, a catalogue error limit), AstroImageJ's
automatic comparisons (no neighbour, not too bright on the frame) and the AAVSO guide (similar colour and brightness,
close, not variable, away from the edge). `judge` returns a row for every catalogue star brighter than the target
+ 3 mag, each either `chosen` or with the first rule it fails, in the order of REASONS; the stars that pass are ranked
by colour and brightness closeness (each scaled by its tolerance, equal weights), then nearness.
"""

from dataclasses import dataclass

import numpy as np

REASONS = ("too_bright", "too_faint", "catalogue_error", "variable_vsx", "variable_gcvs", "variable_gaia",
           "noisy_gaia", "too_far", "edge", "neighbour", "saturated", "non_linear", "low_snr", "colour")  # fmt: skip


@dataclass
class ComparisonRules:
    brighter_by_max: float = 1.5
    fainter_by_max: float = 1.0
    colour_tolerance: float = 0.5
    colour_required: bool = False
    max_distance_arcmin: float | None = None
    catalogue_error_max: float = 0.03
    exclude_variables: bool = True
    exclude_gaia_noisy: bool = True
    r_ap: float = 6.0
    r_out: float = 15.0
    fwhm: float = 3.0
    saturation: float | None = None
    linearity: float | None = None
    edge_margin_px: float | None = None  # None: max(3 r_out, the night's drift + r_out)
    min_snr: float = 100.0
    count: int = 8


def _peak(frame, x, y, half=3):
    yi, xi = int(round(y)), int(round(x))
    box = frame[max(0, yi - half) : yi + half + 1, max(0, xi - half) : xi + half + 1]
    return float(np.nanmax(box)) if box.size else np.nan


def _snr(frame, x, y, r_ap, r_in, r_out):
    yy, xx = np.indices(frame.shape)
    d = np.hypot(xx - x, yy - y)
    ring = frame[(d >= r_in) & (d < r_out)]
    sky, sd = np.median(ring), 1.4826 * np.median(np.abs(ring - np.median(ring)))
    inside = d < r_ap
    flux = float(np.sum(frame[inside] - sky))
    return flux / np.sqrt(max(flux, 0) + inside.sum() * sd * sd) if flux > 0 else 0.0


def judge(stars, target_index, frames=(), shifts=None, rules=None, pixel_scale_arcsec=None, vsx_xy=(), gcvs_xy=()):
    """stars: {"x", "y", "gmag", "bp_rp", "variable", optional "e_gmag", "noisy"} (field.identify's table);
    frames: a sample of images over the night (the first gives the S/N), shifts: their (dx, dy) from the first.
    Returns a list of rows {"index", "x", "y", "mag", "colour", "distance", "peak", "snr", "verdict"}."""
    r = rules or ComparisonRules()
    st = {k: np.asarray(v, float) for k, v in stars.items()}
    x, y, g, col = st["x"], st["y"], st["gmag"], st["bp_rp"]
    n = len(x)
    g_t, c_t = g[target_index], col[target_index]
    shifts = list(shifts) if shifts is not None else [(0.0, 0.0)] * len(frames)
    drift = max((np.hypot(*s) for s in shifts), default=0.0)
    margin = r.edge_margin_px if r.edge_margin_px is not None else max(3 * r.r_out, drift + r.r_out)
    ny, nx = np.shape(frames[0]) if len(frames) else (np.inf, np.inf)
    dist_px = np.hypot(x - x[target_index], y - y[target_index])
    vsx, gcvs = (np.asarray(v, float).reshape(-1, 2) for v in (vsx_xy, gcvs_xy))
    rows, passed = [], []
    for i in range(n):
        if i == target_index or g[i] > g_t + 3:
            continue
        peaks = [_peak(f, x[i] + dx, y[i] + dy) for f, (dx, dy) in zip(frames, shifts, strict=True)]
        peak = max(peaks) if peaks else np.nan
        snr = _snr(frames[0], x[i], y[i], r.r_ap, r.r_ap + 2, r.r_out) if len(frames) else np.nan
        d = np.hypot(x - x[i], y - y[i])
        checks = {
            "too_bright": g[i] < g_t - r.brighter_by_max,
            "too_faint": g[i] > g_t + r.fainter_by_max,
            "catalogue_error": "e_gmag" in st and st["e_gmag"][i] > r.catalogue_error_max,
            "variable_vsx": r.exclude_variables and len(vsx) > 0 and np.hypot(*(vsx - [x[i], y[i]]).T).min() < 3,
            "variable_gcvs": r.exclude_variables and len(gcvs) > 0 and np.hypot(*(gcvs - [x[i], y[i]]).T).min() < 3,
            "variable_gaia": r.exclude_variables and bool(st["variable"][i]),
            "noisy_gaia": r.exclude_gaia_noisy and "noisy" in st and bool(st["noisy"][i]),
            "too_far": r.max_distance_arcmin is not None and pixel_scale_arcsec is not None
            and dist_px[i] * pixel_scale_arcsec / 60 > r.max_distance_arcmin,
            "edge": not (margin <= x[i] <= nx - 1 - margin and margin <= y[i] <= ny - 1 - margin),
            "neighbour": bool(np.any((d > 0.5) & (((d < r.r_out) & (g < g[i] + 5)) | (d < r.r_ap + r.fwhm)))),
            "saturated": r.saturation is not None and peak >= 0.8 * r.saturation,
            "non_linear": r.linearity is not None and peak >= r.linearity,
            "low_snr": np.isfinite(snr) and snr < r.min_snr,
            "colour": r.colour_required and np.isfinite(c_t) and abs(col[i] - c_t) > r.colour_tolerance,
        }  # fmt: skip
        verdict = next((k for k in REASONS if checks[k]), "passed")
        row = {"index": i, "x": float(x[i]), "y": float(y[i]), "mag": float(g[i]), "colour": float(col[i]),
               "distance": float(dist_px[i]), "peak": peak, "snr": snr, "verdict": verdict}  # fmt: skip
        rows.append(row)
        if verdict == "passed":
            passed.append(row)

    def rank(row):
        dc = abs(row["colour"] - c_t) / r.colour_tolerance if np.isfinite(c_t) and np.isfinite(row["colour"]) else 0
        dm = abs(row["mag"] - g_t) / max(r.brighter_by_max, r.fainter_by_max)
        return (dc + dm, row["distance"])

    for k, row in enumerate(sorted(passed, key=rank)):
        row["verdict"] = "chosen" if k < r.count else "not_needed"
    return rows


def most_common_reasons(rows, k=3):
    """The k rules that removed the most stars (for the "no comparison star" advice with its relax buttons)."""
    reasons = [r["verdict"] for r in rows if r["verdict"] in REASONS]
    names, counts = np.unique(reasons, return_counts=True)
    return [str(names[i]) for i in np.argsort(-counts)[:k]]


def suggest(images, offsets, inputs, params, data, header):
    """PHO-17: the user's rules (comprules.ComparisonRules fields as a dict) judged on ten frames spread over the
    night; "catalogue" carries the table with a verdict for every star."""
    from ..calibration.masters import load
    from ..io.inspect import saturation_level

    field = inputs["field"]
    st = field["stars"]
    tx, ty = inputs["target_xy"]
    i_t = int(np.argmin(np.hypot(np.asarray(st["x"]) - tx, np.asarray(st["y"]) - ty)))
    rules = ComparisonRules(**({"saturation": saturation_level(header, data), "count": params["n"],
                                "r_out": params["r_out"]} | dict(params["rules"])))  # fmt: skip
    pick = np.unique(np.linspace(0, len(images) - 1, min(10, len(images))).round().astype(int))
    frames = [data if k == 0 else load(images[k])[0] for k in pick]
    shifts = [tuple(offsets[k]) if len(offsets) else (0.0, 0.0) for k in pick]
    rows = judge(st, i_t, frames, shifts, rules, field.get("scale"),
                 [(v["x"], v["y"]) for v in field.get("variables", [])],
                 [(v["x"], v["y"]) for v in field.get("gcvs", [])])  # fmt: skip
    chosen = [r for r in rows if r["verdict"] == "chosen"]
    if not chosen and not params["rules"]:  # the defaults found none: the older, looser choice, with the table
        from .field import comparison_stars

        old = comparison_stars(field, inputs["target_xy"], data, rules.saturation, n=params["n"], r_out=rules.r_out,
                               margin=60 + int(np.ceil(np.abs(offsets).max())) if len(offsets) else 60)  # fmt: skip
        return {"comps_xy": [[x, y] for x, y, *_ in old["stars"]], "catalogue": old | {"table": rows}}
    if not chosen:
        reasons = ", ".join(most_common_reasons(rows))
        raise ValueError(f"no comparison star passed the rules; most were removed by: {reasons}")
    colour = float(np.asarray(st["bp_rp"], float)[i_t])
    same = all(abs(r["colour"] - colour) <= rules.colour_tolerance for r in chosen) if np.isfinite(colour) else True
    catalogue = {"stars": [(r["x"], r["y"], r["mag"], r["colour"]) for r in chosen], "colour": colour,
                 "same_colour": bool(same), "table": rows}  # fmt: skip
    return {"comps_xy": [[r["x"], r["y"]] for r in chosen], "catalogue": catalogue}
