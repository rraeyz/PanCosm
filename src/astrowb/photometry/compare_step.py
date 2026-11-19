"""photometry.compare_minimum_methods: one eclipse timed by every eclipse method (timeseries.timing_methods)."""

import numpy as np

from ..engine.steps import step

ECLIPSE_METHODS = ("kvw", "mikulasek", "polynomial", "gaussian", "lorentzian", "bisector")


@step("photometry.compare_minimum_methods", inputs=("light_curve",), outputs=("comparison",))
def compare_minimum_methods_step(inputs, params, ctx):
    """The same minimum by each eclipse method: rows of time, error and difference from Kwee–van Woerden (s)."""
    from ..timeseries.minima import dips
    from ..timeseries.timing_methods import compare_methods

    lc = inputs["light_curve"]
    t, y = np.asarray(lc["time"], float), np.asarray(lc["rel_flux"], float)
    err = np.asarray(lc["rel_flux_err"], float) if lc.get("rel_flux_err") else None
    med = np.median(y)
    n = dips(t, y / med)
    if n == 0:
        raise ValueError("no eclipse or transit stands out of the noise in this light curve: do the frames cover it?")
    if n > 1:
        raise ValueError(f"the light curve shows {n} eclipses: compare the methods on a light curve with one")
    c = compare_methods(t, y / med, None if err is None else err / med, methods=ECLIPSE_METHODS)
    res = c["results"]
    ref = res["kvw"].t_min if "kvw" in res else None
    rows = [{"method": m, "time": r.t_min, "error": r.error,
             "diff_s": None if ref is None else (r.t_min - ref) * 86400.0} for m, r in res.items()]  # fmt: skip
    return {"comparison": {"rows": rows, "time_scale": lc.get("time_scale"), "spread": c["spread"],
                           "disagree": c["disagree"], "asymmetric": c["asymmetric"]}}  # fmt: skip
