"""photometry.transit_fit (plans/photometry.md PHO-26): the exact transit on a measured light curve."""

import numpy as np

from ..core.errors import AppError
from ..engine.params import QT_TRANSLATE_NOOP, P
from ..engine.steps import step

DETRENDS = ("airmass", "fwhm", "sky", "x", "y")


def _series(lc, name):
    if name in ("airmass", "fwhm", "ellipticity"):
        return lc.get(name)
    if name == "sky":
        return [s[0] for s in lc["sky"]] if lc.get("sky") else None
    if name in ("x", "y") and lc.get("xy"):
        return [r[0][0 if name == "x" else 1] for r in lc["xy"]]
    return None


@step(
    "photometry.transit_fit",
    inputs=("light_curve",),
    outputs=("transit",),
    params=[
        P("period", "float", 1.0, unit="d", min=0.0, label=QT_TRANSLATE_NOOP("Steps", "Period"),
          help=QT_TRANSLATE_NOOP("Steps", "Fixed for a single transit")),
        P("tc", "float", 0.0, unit="d", label=QT_TRANSLATE_NOOP("Steps", "Mid-transit time (start)"),
          help=QT_TRANSLATE_NOOP("Steps", "0: the middle of the night")),
        P("k", "float", 0.1, min=0.0, max=0.5, label=QT_TRANSLATE_NOOP("Steps", "Radius ratio (start)"),
          help=QT_TRANSLATE_NOOP("Steps", "Rp/R★; the square root of the depth")),
        P("a_rs", "float", 8.0, min=1.0, label=QT_TRANSLATE_NOOP("Steps", "Scaled distance (start)"),
          help=QT_TRANSLATE_NOOP("Steps", "a/R★")),
        P("b", "float", 0.3, min=0.0, max=1.5, label=QT_TRANSLATE_NOOP("Steps", "Impact parameter (start)"),
          help=QT_TRANSLATE_NOOP("Steps", "0: across the centre of the star")),
        P("u1", "float", 0.4, label=QT_TRANSLATE_NOOP("Steps", "Limb darkening u1"),
          help=QT_TRANSLATE_NOOP("Steps", "Quadratic law; fixed unless chosen to fit")),
        P("u2", "float", 0.2, label=QT_TRANSLATE_NOOP("Steps", "Limb darkening u2"),
          help=QT_TRANSLATE_NOOP("Steps", "Quadratic law; fixed unless chosen to fit")),
        P("eclipse", "bool", False, label=QT_TRANSLATE_NOOP("Steps", "Fit the eclipse"),
          help=QT_TRANSLATE_NOOP("Steps", "The secondary eclipse (circular orbit, half a period after the transit) "
                                 "instead of the transit; the shape stays as given")),
        P("occ", "float", 0.001, min=0.0, max=5.0, label=QT_TRANSLATE_NOOP("Steps", "Eclipse depth (start)"),
          help=QT_TRANSLATE_NOOP("Steps", "The companion's light as a fraction of the star's")),
        P("detrend", "text", "airmass", label=QT_TRANSLATE_NOOP("Steps", "Detrend against"),
          help=QT_TRANSLATE_NOOP("Steps", "Comma-separated: airmass, fwhm, sky, x, y (empty: none)")),
        P("fit_ld", "bool", False, label=QT_TRANSLATE_NOOP("Steps", "Fit the limb darkening"),
          help=QT_TRANSLATE_NOOP("Steps", "A single night rarely decides it: leave it fixed")),
        P("red_noise", "bool", False, label=QT_TRANSLATE_NOOP("Steps", "Account for red noise"),
          help=QT_TRANSLATE_NOOP("Steps", "The errors multiplied by β, the time-averaging factor of the residuals")),
        P("mcmc_steps", "int", 0, min=0, max=100000, label=QT_TRANSLATE_NOOP("Steps", "MCMC steps"), advanced=True,
          help=QT_TRANSLATE_NOOP("Steps", "Posterior errors after the fit (the chains stop earlier once converged); "
                                 "0: none")),
    ],
)  # fmt: skip
def transit_fit_step(inputs, params, ctx):
    """The exact transit (quadratic limb darkening) with the chosen detrending; values, errors, derived values and
    fit statistics (photometry.transitfit)."""
    from .transitfit import fit

    lc = inputs["light_curve"]
    t = np.asarray(lc["time"], float)
    f, e = np.asarray(lc["rel_flux"], float), np.asarray(lc["rel_flux_err"], float)
    names = [n.strip() for n in params["detrend"].split(",") if n.strip()]
    unknown = [n for n in names if n not in DETRENDS]
    if unknown:
        raise AppError("unknown detrending series: {name}", name=unknown[0])
    detrend = {n: s for n in names if (s := _series(lc, n)) is not None}
    tc = params["tc"] or float(np.median(t))
    start = {"tc": tc, "k": params["k"], "a_rs": params["a_rs"], "b": params["b"], "u1": params["u1"],
             "u2": params["u2"], "occ": params["occ"]}  # fmt: skip
    free = ("tc", "k", "a_rs", "b", "baseline") + (("u1", "u2") if params["fit_ld"] else ())
    if params["eclipse"]:
        free = ("tc", "occ", "baseline")
    out = fit(
        t,
        f,
        e,
        params["period"],
        start,
        free,
        detrend=detrend,
        mcmc_steps=params.get("mcmc_steps", 0),
        ctx=ctx,
        red_noise=params.get("red_noise", False),
        eclipse=params["eclipse"],
    )
    out["model"], out["residuals"], out["trend"] = (out[k].tolist() for k in ("model", "residuals", "trend"))
    return {"transit": out}


@step(
    "photometry.neb_check",
    inputs=("images", "target_xy", "comps_xy", "field"),
    outputs=("neb",),
    params=[
        P("depth_ppt", "float", 5.0, unit="ppt", min=0.0, label=QT_TRANSLATE_NOOP("Steps", "Transit depth"),
          help=QT_TRANSLATE_NOOP("Steps", "The depth TESS saw on the target")),
        P("radius_arcsec", "float", 150.0, unit="″", min=0.0, label=QT_TRANSLATE_NOOP("Steps", "Search radius"),
          help=QT_TRANSLATE_NOOP("Steps", "Stars this near the target are checked (TFOP: 2.5′)")),
        P("r_ap", "float", 6.0, unit="px", min=0.5, label=QT_TRANSLATE_NOOP("Steps", "Aperture radius"),
          help=QT_TRANSLATE_NOOP("Steps", "As the light curve's")),
        P("r_in", "float", 10.0, unit="px", min=0.5, label=QT_TRANSLATE_NOOP("Steps", "Sky ring, inner radius"),
          help=QT_TRANSLATE_NOOP("Steps", "As the light curve's")),
        P("r_out", "float", 16.0, unit="px", min=0.5, label=QT_TRANSLATE_NOOP("Steps", "Sky ring, outer radius"),
          help=QT_TRANSLATE_NOOP("Steps", "As the light curve's")),
        P("tc", "float", 0.0, unit="d", label=QT_TRANSLATE_NOOP("Steps", "Predicted mid-transit"),
          help=QT_TRANSLATE_NOOP("Steps", "JD (UTC); 0: no box fit")),
        P("duration_h", "float", 0.0, unit="h", min=0.0, label=QT_TRANSLATE_NOOP("Steps", "Transit duration"),
          help=QT_TRANSLATE_NOOP("Steps", "T14; with the mid-transit time, a box is fitted there on every star")),
        P("apertures", "table", (), advanced=True, label=QT_TRANSLATE_NOOP("Steps", "Several apertures"),
          help=QT_TRANSLATE_NOOP("Steps", "[radius, sky inner, sky outer] triples; each star keeps its best "
                                 "disposition. Empty: the one aperture above")),
    ],
)  # fmt: skip
def neb_check_step(inputs, params, ctx):
    """Nearby-eclipsing-binary check (TFOP): every Gaia star near the target that could make the depth, measured on
    every frame, with its disposition (photometry.neb)."""
    from . import neb

    tc, half = params.get("tc") or 0.0, (params.get("duration_h") or 0.0) / 48
    args = (inputs["images"], inputs["target_xy"], inputs["comps_xy"], inputs["field"], params["depth_ppt"])
    tail = (params["radius_arcsec"], ctx, (tc - half, tc + half) if tc and half else None)
    if params.get("apertures"):
        rows = neb.run_apertures(*args, [tuple(a) for a in params["apertures"]], *tail)
    else:
        rows = neb.run(*args, params["r_ap"], params["r_in"], params["r_out"], *tail)
    return {"neb": rows}
