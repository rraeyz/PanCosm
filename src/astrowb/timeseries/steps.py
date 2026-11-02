"""Time-series steps that are not tied to photometry: frequency analysis with prewhitening."""

import numpy as np

from ..engine.params import QT_TRANSLATE_NOOP, P
from ..engine.steps import step


@step(
    "timeseries.frequencies",
    inputs=("time", "flux"),
    outputs=(
        "frequencies",
        "grid",
        "spectrum",
        "residual_spectrum",
        "window",
        "maxima",
        "rms",
        "t_ref",
        "zero_point",
        "clean_spectrum",
    ),
    params=(
        P(
            "f_max",
            "float",
            50.0,
            unit="c/d",
            min=0.0,
            label=QT_TRANSLATE_NOOP("Steps", "Highest frequency"),
            help=QT_TRANSLATE_NOOP("Steps", "The spectrum is computed from 0 up to this frequency"),
        ),
        P(
            "n_max",
            "int",
            10,
            min=1,
            max=200,
            label=QT_TRANSLATE_NOOP("Steps", "Most frequencies"),
            help=QT_TRANSLATE_NOOP("Steps", "Prewhitening stops after this many frequencies"),
        ),
        P(
            "snr_min",
            "float",
            4.0,
            min=0.0,
            label=QT_TRANSLATE_NOOP("Steps", "Smallest S/N"),
            help=QT_TRANSLATE_NOOP("Steps", "A peak below this signal-to-noise ends the prewhitening (Breger 1993: 4)"),
        ),
        P(
            "magnitudes",
            "bool",
            False,
            label=QT_TRANSLATE_NOOP("Steps", "Magnitudes"),
            help=QT_TRANSLATE_NOOP(
                "Steps", "The values are magnitudes (brighter is smaller), for the times of maximum"
            ),
        ),
        P(
            "clean",
            "bool",
            False,
            label=QT_TRANSLATE_NOOP("Steps", "CLEAN spectrum"),
            advanced=True,
            help=QT_TRANSLATE_NOOP(
                "Steps", "Also a spectrum with the aliases of the sampling removed (Roberts et al. 1987)"
            ),
        ),
    ),
)
def frequencies_step(inputs, params, ctx):
    """Amplitude spectrum, spectral window, prewhitened multi-frequency fit and times of maximum."""
    from . import fourier

    t, y = np.asarray(inputs["time"], float), np.asarray(inputs["flux"], float)
    ok = np.isfinite(t) & np.isfinite(y)
    t, y = t[ok], y[ok]
    fit, grid, first, resid, snr = fourier.prewhiten(
        t, y, params["f_max"], params["n_max"], params["snr_min"], progress=lambda f: ctx.progress(f, "fit")
    )
    rows, maxima = [], []
    if fit is not None:
        for k in np.argsort(-fit["amp"]):
            keys = ("freq", "freq_err", "amp", "amp_err", "phase", "phase_err")
            rows.append({key: float(fit[key][k]) for key in keys} | {"snr": float(snr[k])})
        maxima = [list(m) for m in fourier.times_of_maximum(t, y, fit, magnitudes=params["magnitudes"])]
    clean_spec = None
    if params["clean"]:  # aliases of the sampling removed (CLEAN), on the same grid as the other spectra
        ctx.progress(0.9, "fit")
        f_c, a_c, _ = fourier.clean(t, y, params["f_max"])
        clean_spec = np.interp(grid, f_c, a_c).tolist()
    return {
        "clean_spectrum": clean_spec,
        "frequencies": rows,
        "grid": grid.tolist(),
        "spectrum": first.tolist(),
        "residual_spectrum": resid.tolist(),
        "window": fourier.spectral_window(t, grid).tolist(),
        "maxima": maxima,
        "rms": None if fit is None else fit["rms"],
        "t_ref": None if fit is None else fit["t_ref"],
        "zero_point": None if fit is None else fit["zero_point"],
    }


@step(
    "timeseries.survey_lc",
    inputs=("target",),
    outputs=("light_curve",),
    optional=("cache_file",),
    params=(
        P(
            "source",
            "choice",
            "ZTF",
            choices=("ZTF", "AAVSO"),
            label=QT_TRANSLATE_NOOP("Steps", "Archive"),
            help=QT_TRANSLATE_NOOP("Steps", "Where the light curve comes from"),
        ),
        P(
            "band",
            "band",
            None,
            label=QT_TRANSLATE_NOOP("Steps", "Band"),
            help=QT_TRANSLATE_NOOP("Steps", "One band of the archive; empty: the first"),
        ),
    ),
)
def survey_lc_step(inputs, params, ctx):
    """ZTF (IRSA) or AAVSO light curve of a star, one band, times in BJD_TDB (needs the internet)."""
    from ..planning.targets import Resolver, TargetError
    from . import surveys

    ctx.progress(0.05, "catalogue")
    coord = None
    try:
        coord = Resolver(inputs.get("cache_file") or "targets.json").resolve(inputs["target"]).coord
    except (TargetError, OSError, ValueError):
        if params["source"] == "ZTF":
            raise
    if params["source"] == "ZTF":
        rows = surveys.ztf(coord)
    else:
        rows = surveys.aavso(inputs["target"])
    if not rows:
        raise ValueError(f"no {params['source']} light curves for {inputs['target']}")
    return {"light_curve": surveys.to_light_curve(rows, coord, params["band"], params["source"])}


@step(
    "timeseries.oc_fit",
    inputs=("minima",),
    outputs=("fit",),
    params=(
        P(
            "model",
            "choice",
            "ltte",
            choices=("ltte", "apsidal"),
            label=QT_TRANSLATE_NOOP("Steps", "Model"),
            help=QT_TRANSLATE_NOOP("Steps", "Third body (light-travel time) or apsidal motion"),
        ),
        P(
            "t0",
            "time",
            0.0,
            unit="d",
            label=QT_TRANSLATE_NOOP("Steps", "Reference T0"),
            help=QT_TRANSLATE_NOOP("Steps", "Epoch zero of the ephemeris"),
        ),
        P(
            "period",
            "float",
            1.0,
            unit="d",
            min=0.0,
            label=QT_TRANSLATE_NOOP("Steps", "Period"),
            help=QT_TRANSLATE_NOOP("Steps", "Period of the ephemeris used to count the cycles"),
        ),
        P(
            "mcmc_steps",
            "int",
            0,
            min=0,
            max=1_000_000,
            label=QT_TRANSLATE_NOOP("Steps", "MCMC steps"),
            advanced=True,
            help=QT_TRANSLATE_NOOP(
                "Steps",
                "The most steps of the Markov chains for the errors (they stop earlier once converged); 0: none",
            ),
        ),
    ),
)
def oc_fit_step(inputs, params, ctx):
    """Third-body or apsidal-motion fit to "time [error] [I/II]" lines, with MCMC errors when mcmc_steps > 0: a task,
    so the page stays usable during the chain and it can be cancelled."""
    from .ephemeris import parse_minima
    from .oc_models import fit_apsidal, fit_ltte

    minima = parse_minima(inputs["minima"])
    fit = {"ltte": fit_ltte, "apsidal": fit_apsidal}[params["model"]]
    ctx.progress(0.02, "fit")
    return {"fit": fit(minima, params["t0"], params["period"], mcmc_steps=params["mcmc_steps"], ctx=ctx)}
