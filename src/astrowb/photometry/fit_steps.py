"""photometry.transit_fit (plans/photometry.md PHO-26): the exact transit on a measured light curve."""

import numpy as np

from ..engine.params import QT_TRANSLATE_NOOP, P
from ..engine.steps import step

DETRENDS = ("airmass", "fwhm", "sky", "x", "y")


def _series(lc, name):
    if name in ("airmass", "fwhm"):
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
        P("detrend", "text", "airmass", label=QT_TRANSLATE_NOOP("Steps", "Detrend against"),
          help=QT_TRANSLATE_NOOP("Steps", "Comma-separated: airmass, fwhm, sky, x, y (empty: none)")),
        P("fit_ld", "bool", False, label=QT_TRANSLATE_NOOP("Steps", "Fit the limb darkening"),
          help=QT_TRANSLATE_NOOP("Steps", "A single night rarely decides it: leave it fixed")),
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
        name = unknown[0]
        raise ValueError(f"unknown detrending series: {name}")
    detrend = {n: s for n in names if (s := _series(lc, n)) is not None}
    tc = params["tc"] or float(np.median(t))
    start = {"tc": tc, "k": params["k"], "a_rs": params["a_rs"], "b": params["b"], "u1": params["u1"],
             "u2": params["u2"]}  # fmt: skip
    free = ("tc", "k", "a_rs", "b", "baseline") + (("u1", "u2") if params["fit_ld"] else ())
    out = fit(t, f, e, params["period"], start, free, detrend=detrend)
    out["model"], out["residuals"] = out["model"].tolist(), out["residuals"].tolist()
    return {"transit": out}
