"""Sentence parts of the methods templates for the O-C, frequency, nearby-EB, plate-solving and spectroscopy steps
(core/methods.py joins them to the recorded parameters)."""


def _extraction(p):
    return {"extraction": "optimal extraction" if p.get("optimal", True) else "boxcar extraction"}


def _oc(p):
    model = (
        "the light-travel-time effect of a third body (Irwin 1952)"
        if p["model"] == "ltte"
        else "first-order apsidal motion (Gimenez & Garcia-Pelayo 1983)"
    )
    mcmc = f", with errors from Markov chains of at most {p['mcmc_steps']} steps" if p["mcmc_steps"] else ""
    return {"model_clause": model, "mcmc_clause": mcmc}


def _neb(p):
    if p.get("apertures"):
        ap = f"every star was measured on every frame with {len(p['apertures'])} apertures, the best disposition kept"
    else:
        ap = (
            f"every star was measured on every frame with an aperture of {p['r_ap']:g} pixels "
            f"(sky ring {p['r_in']:g} to {p['r_out']:g} pixels)"
        )
    box = ", and a box was fitted to each star in the predicted transit window" if p["tc"] and p["duration_h"] else ""
    return {"aperture_clause": ap, "box_clause": box}


def _rv(p):
    if p["method"] == "bf":
        n = p["components"]
        how = f"by the broadening function with {n} rotational profile{'s' if n != 1 else ''} (Rucinski 1992, 2002)"
    else:
        how = "by cross-correlation (TODCOR for a second template; Zucker & Mazeh 1994)"
    return {"method_clause": how}


def _frequencies(p):
    return {
        "clean_clause": "; the aliases of the sampling were removed by CLEAN (Roberts et al. 1987)"
        if p["clean"]
        else ""
    }


def _solve(p):
    gaia = ", and the solution was refitted to Gaia DR3 stars where the catalogue could be reached"
    return {"refine_clause": gaia if p["refine_gaia"] else ""}


PARTS = {
    "timeseries.oc_fit": _oc,
    "timeseries.frequencies": _frequencies,
    "photometry.neb_check": _neb,
    "astrometry.solve": _solve,
    "spectroscopy.reduce": _extraction,
    "spectroscopy.echelle": _extraction,
    "spectroscopy.rv": _rv,
}
