"""Binary-star modelling as engine steps."""

from pathlib import Path

import numpy as np

from ..engine.steps import step
from . import data, fit


@step(
    "models.eb_fit",
    inputs=("light_curve", "start"),
    outputs=("model",),
    optional=("orbit", "export_dir"),
    free=None,
    ld1=(0.0, 0.0),
    ld2=(0.0, 0.0),
    mcmc_steps=0,
    export_format="phoebe",
    exposure=0.0,
)
def eb_fit_step(inputs, params, ctx):
    """Fit the detached-binary / transit model to a light-curve file; absolute dimensions when a
    double-lined orbit is given; PHOEBE start files when export_dir is given."""
    t, flux, err, info = data.read_light_curve(inputs["light_curve"])
    ctx.progress(0.2, "fit")
    start = inputs["start"] | {"exposure": params["exposure"]}  # seconds; 0: the flux at each time
    r = fit.fit_light_curve(t, flux, err, start, params["free"], params["ld1"], params["ld2"])
    p = r["params"]
    phase = ((t - p["t0"]) / p["period"] + 0.25) % 1 - 0.25
    grid = np.linspace(-0.25, 0.75, 1500)
    out = r | {
        "info": info,
        "phase": phase.tolist(),
        "flux": (flux / r["scale"]).tolist(),
        "model_phase": grid.tolist(),
        "model_flux": fit.model(p["t0"] + grid * p["period"], p, params["ld1"], params["ld2"]).tolist(),
        "residual": (flux / r["scale"] - fit.model(t, p, params["ld1"], params["ld2"])).tolist(),
        "absolute": None,
    }
    if params["mcmc_steps"]:  # posterior uncertainties: slower, more honest for correlated parameters
        out["mcmc"] = fit.mcmc(t, flux, err, r, params["free"], params["ld1"], params["ld2"], params["mcmc_steps"], ctx)
    if inputs.get("orbit"):
        out["absolute"] = fit.absolute_dimensions(r, inputs["orbit"])
    orbit, absolute = inputs.get("orbit") or {}, out["absolute"] or {}
    q = absolute["m2"] / absolute["m1"] if absolute.get("m1") else None
    if q is None and orbit.get("k") and orbit.get("k2"):
        q = orbit["k"] / orbit["k2"]  # M2/M1 = K1/K2
    out["roche"] = fit.roche_check(r["derived"]["r1"], r["derived"]["r2"], q)
    if inputs.get("export_dir") and params["export_format"] == "wd":
        from .wd import write_wd_files

        orbit_info = {"gamma": orbit.get("gamma", 0.0), "a": absolute.get("a")} if orbit else None
        out["exported"] = write_wd_files(inputs["export_dir"], t, flux, err, r, q, orbit=orbit_info)
    elif inputs.get("export_dir") and params["export_format"] == "transit":
        from . import transit_report

        name = Path(inputs["light_curve"]).stem
        out["exported"], out["transit"] = transit_report.write(
            inputs["export_dir"], t, flux, err, r, lambda tt: fit.model(tt, p, params["ld1"], params["ld2"]), name
        )
    elif inputs.get("export_dir"):
        out["exported"] = data.export_for_phoebe(inputs["export_dir"], t, flux, err, r, absolute=out["absolute"])
    return {"model": out}


@step("models.visual_orbit", inputs=("measures",), outputs=("orbit",), p_min=None, p_max=None, parallax_mas=None)
def visual_orbit_step(inputs, params, ctx):
    """Visual-binary orbit from "epoch theta rho [rho_err] [theta_err]" lines (see models/visual.py)."""
    from . import visual

    ctx.progress(0.1, "fit")
    t, th, rho, rho_err, th_err = visual.parse_measures(inputs["measures"])
    p_range = (params["p_min"], params["p_max"]) if params["p_min"] and params["p_max"] else None
    plx = params["parallax_mas"] / 1000.0 if params["parallax_mas"] else None
    orbit = visual.fit(t, th, rho, rho_err, th_err, p_range=p_range, parallax=plx)
    orbit |= {"epoch": t.tolist(), "theta": th.tolist(), "rho": rho.tolist()}
    return {"orbit": orbit}
