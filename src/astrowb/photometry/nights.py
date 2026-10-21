"""Several nights of one star joined into one light curve (plans/photometry.md item 12). Nights measured with the
same star list share their comparison stars; each night's ensemble is put on the same zero point by the stars'
shares of the whole ensemble on the frames that have every star, so a star missing for a whole night (the field
placed a little differently) does not make a step. Then the nights are one
curve in time order; with T0 and the period the minimum step times every eclipse in it, all going to O−C at once."""

import numpy as np

from .differential import ensemble


def join_nights(nights):
    """nights: light curves (time, target_flux, target_flux_err, comp_flux, comp_flux_err) measured with the same
    comparison stars, in the same order. The fluxes of all nights in one ensemble (differential.ensemble): the frames
    with every star give each star's share, and a night that lacks a star is scaled by the share it lacks, so the
    nights meet on one zero point. Returns one light curve in time order with the raw fluxes (the Photometry window
    recomputes from them), "night" (index per point) and "night_offsets" (mag the joining moved each night)."""
    if len(nights) < 2:
        raise ValueError("join needs two nights or more")
    mixed_standards(nights)
    comps = [np.asarray(lc["comp_flux"], float).reshape(len(lc["time"]), -1) for lc in nights]
    if len({c.shape[1] for c in comps}) != 1:
        raise ValueError("the nights were measured with different numbers of comparison stars")
    if not any(np.isfinite(c).all(axis=1).any() for c in comps):
        raise ValueError("no night has a frame with every comparison star")
    cat = {k: np.concatenate([np.asarray(lc[k], float).reshape(len(lc["time"]), -1).squeeze(-1)
                              if k in ("time", "target_flux", "target_flux_err") else
                              np.asarray(lc[k], float).reshape(len(lc["time"]), -1) for lc in nights])
           for k in ("time", "target_flux", "target_flux_err", "comp_flux", "comp_flux_err")}  # fmt: skip
    night = np.concatenate([np.full(len(lc["time"]), k) for k, lc in enumerate(nights)])
    rel, err = ensemble(cat["target_flux"], cat["target_flux_err"], cat["comp_flux"], cat["comp_flux_err"])
    offsets = []
    for k, (lc, c) in enumerate(zip(nights, comps, strict=True)):
        alone, _ = ensemble(
            lc["target_flux"],
            lc["target_flux_err"],
            c,
            np.nan_to_num(np.asarray(lc["comp_flux_err"], float)).reshape(c.shape),
        )
        offsets.append(float(2.5 * np.log10(np.nanmedian(alone) / np.nanmedian(rel[night == k]))))
    order = np.argsort(cat["time"])
    files = [f for lc in nights for f in (lc.get("file") or [""] * len(lc["time"]))]
    out = {k: v[order].tolist() for k, v in cat.items()}
    out |= {"rel_flux": rel[order].tolist(), "rel_flux_err": err[order].tolist(), "night": night[order].tolist(),
            "night_offsets": offsets, "file": [files[i] for i in order],
            "time_scale": nights[0].get("time_scale", "BJD_TDB")}  # fmt: skip
    return out


def mixed_standards(curves):
    """A join of BJD_TDB with HJD_UTC is wrong by up to minutes: refused, never done silently (ARC-15 item 2)."""
    scales = sorted({lc.get("time_scale") for lc in curves if lc.get("time_scale")})
    if len(scales) > 1:
        raise ValueError(f"the light curves have times in different standards ({', '.join(scales)}): convert them "
                         "to one first")  # fmt: skip


def read_export(path):
    """A light curve written by the Photometry window's CSV export (time column first, target_flux, comp<i>_flux,
    rel_flux, rel_flux_err), back as a light curve for join_nights."""
    from astropy.table import Table

    t = Table.read(path, format="csv")
    cols = t.colnames
    comp = sorted((c for c in cols if c.startswith("comp") and c.endswith("_flux")), key=lambda c: int(c[4:-5]))
    if "target_flux" not in cols or not comp:
        raise ValueError("not a light curve exported from the Photometry window (CSV)")
    f = np.asarray(t["target_flux"], float)
    rel, rel_err = np.asarray(t["rel_flux"], float), np.asarray(t["rel_flux_err"], float)
    c = np.column_stack([np.asarray(t[k], float) for k in comp])
    frac = np.where(rel > 0, rel_err / rel, 0.0)  # the export keeps relative errors only: shared by the stars
    return {"time": np.asarray(t[cols[0]], float).tolist(), "time_scale": cols[0], "target_flux": f.tolist(),
            "target_flux_err": (f * frac / np.sqrt(2)).tolist(), "comp_flux": c.tolist(),
            "comp_flux_err": (c * frac[:, None] / np.sqrt(2)).tolist(), "rel_flux": rel.tolist(),
            "rel_flux_err": rel_err.tolist()}  # fmt: skip
