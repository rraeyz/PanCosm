"""TESS and Kepler/K2 light curves from the MAST archive, as light curves the other tools understand.

The mission pipelines' light-curve files (SPOC for TESS, the Kepler pipeline for Kepler/K2) carry times in
BJD_TDB minus a reference (BJDREFI + BJDREFF: 2457000 for TESS, 2454833 for Kepler) and the PDCSAP flux,
corrected for instrumental trends. Points flagged by the pipeline (QUALITY != 0) are dropped; each file
(sector / quarter) is divided by its median, so several can be joined.
"""

from pathlib import Path

import numpy as np

MISSIONS = ("TESS", "Kepler", "K2")


def read_mission_lc(path, flux="PDCSAP"):
    """{time (BJD_TDB), rel_flux, rel_flux_err, ...} of one pipeline light-curve file."""
    from astropy.io import fits

    with fits.open(path) as hdul:
        head = hdul[0].header
        lc = hdul["LIGHTCURVE"]
        h, d = lc.header, lc.data
        ref = float(h.get("BJDREFI", 0)) + float(h.get("BJDREFF", 0.0))
        t = np.asarray(d["TIME"], float) + ref
        f = np.asarray(d[f"{flux}_FLUX"], float)
        e = np.asarray(d[f"{flux}_FLUX_ERR"], float)
        q = np.asarray(d["QUALITY"]) if "QUALITY" in d.names else np.zeros(len(t), int)
    ok = np.isfinite(t) & np.isfinite(f) & np.isfinite(e) & (q == 0)
    med = np.median(f[ok]) if ok.any() else np.nan
    part = head.get("SECTOR", head.get("QUARTER", head.get("CAMPAIGN", "")))
    if "CAMPAIGN" in head:  # K2 files say TELESCOP = Kepler, MISSION = K2
        part = f"C{part}"
    return {
        "time": t[ok].tolist(),
        "rel_flux": (f[ok] / med).tolist(),
        "rel_flux_err": (e[ok] / med).tolist(),
        "time_scale": "BJD_TDB",
        "source": f"{head.get('MISSION', head.get('TELESCOP', '')).strip()} {part}".strip(),
    }


def join(curves):
    """Several sectors / quarters into one light curve, in time order."""
    from ..photometry.nights import mixed_standards

    mixed_standards(curves)
    keys = ("time", "rel_flux", "rel_flux_err")
    t, f, e = (np.concatenate([np.asarray(c[k], float) for c in curves]) for k in keys)
    order = np.argsort(t)
    return {
        "time": t[order].tolist(),
        "rel_flux": f[order].tolist(),
        "rel_flux_err": e[order].tolist(),
        "time_scale": "BJD_TDB",
        "source": ", ".join(c["source"] for c in curves),
    }


def download(target, mission, folder, author=None, observations=None, max_files=30):
    """Pipeline light-curve files of a target (name or 'RA Dec') into folder; returns their paths."""
    if not str(target).strip():
        raise ValueError("give the target's name or coordinates")
    given = observations is not None
    if not given:
        from astroquery.mast import Observations as observations
    from astroquery.mast import conf

    def lookup():
        collection = "K2" if mission == "K2" else mission
        with conf.set_temp("timeout", 120):  # an archive that stops answering must not hold the task forever
            obs = observations.query_criteria(
                objectname=target, radius="0.001 deg", obs_collection=collection, dataproduct_type="timeseries"
            )
        if len(obs) == 0:
            raise ValueError(f"no {mission} light curves for {target}")
        return observations.get_product_list(obs)

    from ..services.cache import cached

    # the archive's list kept a day (ARC-14); a list handed in (tests) is not the archive's and is not kept
    products = lookup() if given else cached("lightcurves", ("mast", str(target).strip(), mission), lookup)
    # light curves: "LC" (TESS), "LLC" (Kepler / K2 long cadence); the product list names the pipeline in
    # "project" (astroquery 0.4.11, 2026; "provenance_name" before)
    lcs = products[np.isin(np.asarray(products["productSubGroupDescription"], str), ["LC", "LLC"])]
    names = np.asarray(lcs["provenance_name" if "provenance_name" in lcs.colnames else "project"], str)
    # TESS: the 2-min SPOC light curves; the full-frame TESS-SPOC ones only when there are none (same sectors)
    for wanted in [author] if author else {"TESS": ["SPOC", "TESS-SPOC"], "Kepler": ["Kepler"], "K2": ["K2"]}[mission]:
        products = lcs[names == wanted]
        if len(products):
            break
    if len(products) == 0:
        raise ValueError(f"no {mission} light curves for {target}")
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    table = observations.download_products(products[:max_files], download_dir=str(folder), cache=True)
    return [str(p) for p in table["Local Path"]]
