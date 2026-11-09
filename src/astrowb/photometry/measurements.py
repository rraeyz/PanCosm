"""The measurements table of a light curve: one row per frame, every number, the columns named as AstroImageJ names
them where they mean the same (its Aperture_.java, read 2026-11-08), so that the two tables can be put side by side
(plans/photometry.md item 6).

Stars are numbered as in AstroImageJ: the target T1, the comparison stars C2, C3 …, further targets and check stars
T after them. AstroImageJ columns that have no counterpart here, and why:
- X(IJ), Y(IJ): ImageJ's pixel convention (the first pixel's centre at 0.5); X(FITS), Y(FITS) carry the same position.
- RA, DEC per star: the positions are measured in pixels; each frame's plate solution is not kept with the curve.
- Mean, Variance, Width, X-Width, Y-Width, Roundness, Angle per star: not measured per star on every frame; the
  frame's FWHM (median of the stars) is FWHM_Mean, as AstroImageJ's own column of that name.
- N_Sky_Pixels: the ring's area before the rejection of stars and outliers (photutils counts the kept ones only).
"""

import numpy as np

AIJ_TIME = ("J.D.-2400000", "JD_UTC", "BJD_TDB")


def star_names(n_comp, n_extra=0):
    """AstroImageJ's aperture names: T1, C2 … C(n+1), then T for the further targets and check stars."""
    return ["T1", *[f"C{k + 2}" for k in range(n_comp)], *[f"T{n_comp + 2 + k}" for k in range(n_extra)]]


def measurements(lc):
    """{column: list} in AstroImageJ's order, and {(row, column): reason} for the cells to colour (saturated)."""
    n = len(lc["file"])
    nan = np.full(n, np.nan)

    def per_frame(key, default):  # a light curve from an older session or another program may lack a column
        value = lc.get(key)
        return default if value is None or len(value) != n else value

    flux = np.column_stack(
        [lc["target_flux"], np.asarray(per_frame("comp_flux", np.zeros((n, 0))), float).reshape(n, -1)]
    )
    err = np.column_stack(
        [per_frame("target_flux_err", nan), np.asarray(per_frame("comp_flux_err", np.full(flux[:, 1:].shape, np.nan)),
                                                         float).reshape(n, -1)]
    )  # fmt: skip
    n_comp = flux.shape[1] - 1
    if lc.get("extra_flux"):
        flux = np.column_stack([flux, lc["extra_flux"]])
        err = np.column_stack([err, lc["extra_flux_err"]])
    names = star_names(n_comp, flux.shape[1] - 1 - n_comp)
    xy = np.asarray(per_frame("xy", np.full((n, flux.shape[1], 2), np.nan)), float)
    sky = np.asarray(per_frame("sky", np.full(flux.shape, np.nan)), float)
    peak = np.asarray(per_frame("peak", np.full(flux.shape, np.nan)), float)
    radii = np.asarray(per_frame("radii", np.full((n, 3), np.nan)), float).reshape(n, 3)
    cols = {"Label": list(lc["file"]), "slice": list(range(1, n + 1))}
    jd = np.asarray(lc.get("jd_utc", [np.nan] * n), float)
    cols["J.D.-2400000"] = (jd - 2400000.0).tolist()
    cols["JD_UTC"] = jd.tolist()
    if lc.get("time_scale") == "BJD_TDB":
        cols["BJD_TDB"] = list(lc["time"])
    if lc.get("airmass") is not None:
        cols["AIRMASS"] = list(lc["airmass"])
    if lc.get("fwhm"):
        cols["FWHM_Mean"] = list(lc["fwhm"])
    with np.errstate(divide="ignore", invalid="ignore"):
        snr = flux / err
        amag = -2.5 * np.log10(flux)
        amag_err = 2.5 / np.log(10) * err / flux
    n_src = np.pi * radii[:, 0] ** 2
    n_sky = np.pi * (radii[:, 2] ** 2 - radii[:, 1] ** 2)
    flags = {}
    level = lc.get("saturation")
    for k, name in enumerate(names):
        has_xy = xy.ndim == 3 and k < xy.shape[1]  # stars added after the measurement have no positions here
        cols[f"X(FITS)_{name}"] = (xy[:, k, 0] + 1).tolist() if has_xy else [np.nan] * n  # FITS: first pixel is 1
        cols[f"Y(FITS)_{name}"] = (xy[:, k, 1] + 1).tolist() if has_xy else [np.nan] * n
        cols[f"Source-Sky_{name}"] = flux[:, k].tolist()
        cols[f"Source_Error_{name}"] = err[:, k].tolist()
        cols[f"Source_SNR_{name}"] = snr[:, k].tolist()
        cols[f"Source_AMag_{name}"] = amag[:, k].tolist()
        cols[f"Source_AMag_Err_{name}"] = amag_err[:, k].tolist()
        cols[f"N_Src_Pixels_{name}"] = n_src.tolist()
        cols[f"Sky/Pixel_{name}"] = sky[:, k].tolist() if sky.ndim == 2 and k < sky.shape[1] else [np.nan] * n
        cols[f"N_Sky_Pixels_{name}"] = n_sky.tolist()
        cols[f"Peak_{name}"] = peak[:, k].tolist() if k < peak.shape[1] else [np.nan] * n
        move = np.asarray(per_frame("centring_move", np.full(flux.shape, np.nan)), float)
        if move.ndim == 2 and k < move.shape[1]:  # not an AstroImageJ column: how far centring moved the star
            cols[f"Centring_Move_{name}"] = move[:, k].tolist()
        cols[f"Source_Radius_{name}"] = radii[:, 0].tolist()
        cols[f"Sky_Rad(min)_{name}"] = radii[:, 1].tolist()
        cols[f"Sky_Rad(max)_{name}"] = radii[:, 2].tolist()
        lin = lc.get("linearity")
        if lin and k < peak.shape[1]:
            for row in np.nonzero(peak[:, k] >= lin)[0]:
                flags[(int(row), f"Peak_{name}")] = f"non-linear: peak {peak[row, k]:.0f} ≥ {lin:.0f}"
        if level and k < peak.shape[1]:  # saturation over non-linearity in the same cell
            for row in np.nonzero(peak[:, k] >= level)[0]:
                flags[(int(row), f"Peak_{name}")] = f"saturated: peak {peak[row, k]:.0f} ≥ {level:.0f}"
    cols["rel_flux_T1"] = list(lc["rel_flux"])
    cols["rel_flux_err_T1"] = list(lc["rel_flux_err"])
    with np.errstate(divide="ignore", invalid="ignore"):
        cols["rel_flux_SNR_T1"] = (np.asarray(lc["rel_flux"]) / np.asarray(lc["rel_flux_err"])).tolist()
    cols["tot_C_cnts"] = flux[:, 1 : 1 + n_comp].sum(axis=1).tolist()
    cols["tot_C_err"] = np.sqrt((err[:, 1 : 1 + n_comp] ** 2).sum(axis=1)).tolist()
    for i, x in enumerate(lc.get("extra") or []):  # further targets / check stars against the same ensemble
        name = names[1 + n_comp + i]
        cols[f"rel_flux_{name}"], cols[f"rel_flux_err_{name}"] = list(x["rel_flux"]), list(x["rel_flux_err"])
    return cols, flags


def filter_rows(cols, expression):
    """Rows kept by an AstroImageJ-style filter such as "rel_flux_err_T1 > 0.0006" (column, operator, number);
    several joined by "and". Returns the row indices. Raises ValueError for an unknown column or a malformed rule."""
    import operator
    import re

    ops = {
        ">": operator.gt,
        "<": operator.lt,
        ">=": operator.ge,
        "<=": operator.le,
        "==": operator.eq,
        "!=": operator.ne,
    }
    n = len(cols["Label"])
    keep = np.ones(n, bool)
    for part in re.split(r"\s+and\s+", expression.strip()):
        if not part:
            continue
        m = re.fullmatch(r"\s*(\S+)\s*(>=|<=|==|!=|>|<)\s*([-+0-9.eE]+)\s*", part)
        if not m:
            raise ValueError(f"filter not understood: {part}")
        name, op, value = m.groups()
        if name not in cols:
            raise ValueError(f"no column {name} in the measurements table")
        with np.errstate(invalid="ignore"):
            keep &= ops[op](np.asarray(cols[name], float), float(value))
    return np.nonzero(keep)[0].tolist()
