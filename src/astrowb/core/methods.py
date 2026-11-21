"""The methods paragraphs of a project's recorded runs (plans/architecture.md ARC-11 item 4, the engine side): one
template per step in resources/methods/<step>.txt, filled with the run's recorded parameters; a step without a
template says nothing. English only, as a paper is."""

from pathlib import Path

from ..brand import BRAND
from ..engine.steps import REGISTRY, get
from .citations import short
from .methods_more import PARTS

DIR = Path(__file__).resolve().parent.parent / "resources" / "methods"


def _extra(step_id, p):
    """Parts of a sentence that depend on a flag; they join the parameters the template can use."""
    if step_id == "calibration.run":
        return {
            "flat_clause": " and flat field" if p.get("divide_flat", True) else "",
            "cosmic_clause": ", and cosmic rays were removed with L.A.Cosmic" if p.get("cosmic_rays") else "",
        }
    if step_id == "photometry.light_curve":
        return {"psf_clause": ", the star fluxes by PSF fitting," if p.get("psf") else ""}
    if step_id == "timeseries.minimum":
        kvw = p["method"] == "kvw"
        ephemeris = p.get("t0") is not None and p.get("period")
        return {
            "method_clause": f"by the method of {short('kwee1956')}" if kvw else f"by the {p['method']} method",
            "ephemeris_clause": f", against T0 = {p['t0']:.5f} and a period of {p['period']:g} d" if ephemeris else "",
        }
    if step_id == "timeseries.period":
        gls = p["method"] == "gls"
        return {
            "upper_clause": f"to {p['p_max']:g} d" if p.get("p_max") else "to half the time the light curve spans",
            "cite_clause": f" following {short('zechmeister2009')}" if gls else "",
        }
    if step_id == "photometry.transit_fit":
        ld = "fitted" if p["fit_ld"] else f"fixed at u1 = {p['u1']:g}, u2 = {p['u2']:g}"
        names = [n.strip() for n in p["detrend"].split(",") if n.strip()]
        return {
            "what": "secondary eclipse" if p["eclipse"] else "transit",
            "ld_clause": f"quadratic limb darkening {ld}",
            "detrend_clause": f", detrended against {', '.join(names)}" if names else "",
            "noise_clause": f"; errors scaled by the β factor ({short('winn2008')})" if p["red_noise"] else "",
            "mcmc_clause": f"; posterior errors from up to {p['mcmc_steps']} MCMC steps" if p["mcmc_steps"] else "",
        }
    if step_id == "models.eb_fit":
        from ..models.fit import DEFAULT_FREE, NAMES

        free = p.get("free") or [n for n in NAMES if n in DEFAULT_FREE]
        return {
            "free_list": ", ".join(free),
            "exposure_clause": f", the model averaged over {p['exposure']:g} s exposures" if p["exposure"] else "",
            "mcmc_clause": f"; posterior errors from up to {p['mcmc_steps']} MCMC steps" if p["mcmc_steps"] else "",
        }
    return PARTS[step_id](p) if step_id in PARTS else {}


def methods(runs):
    """Paragraph for the successful runs (Project.runs() dicts, in order); a step repeated gives one sentence per run
    only when its parameters differ."""
    seen, out = set(), []
    for r in runs:
        template = DIR / f"{r['step']}.txt"
        if r.get("status") != "done" or not template.is_file():
            continue
        get(r["step"])  # loads the built-in steps
        p = REGISTRY[r["step"]].defaults | (r.get("params") or {})
        version = (r.get("environment") or {}).get("app", "")
        text = (
            template.read_text(encoding="utf-8")
            .strip()
            .format_map({**p, **_extra(r["step"], p), "software": BRAND.display_name, "version": version})
        )
        if text not in seen:
            seen.add(text)
            out.append(text)
    return " ".join(out)
