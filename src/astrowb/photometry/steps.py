"""Photometry and timing as engine steps."""

import numpy as np

from .. import timing
from ..engine.params import QT_TRANSLATE_NOOP, P
from ..engine.steps import REGISTRY, describe, step
from ..hdr import get
from ..io.lzw import readable
from ..timeseries.minima import kwee_van_woerden, o_minus_c, trapezoid_fit
from .lightcurve import light_curve
from .measure_params import MEASURE as _MEASURE
from .recipe import placed_by_sky
from .stacked import combined


def _check_positions(image, target, comps=()):
    """Stars given outside the frame (a typo, the wrong frame's coordinates) are named, before photometry fails
    with a message about arrays."""
    from ..calibration.masters import load

    ny, nx = load(image)[0].shape[-2:]
    if not (0 <= target[0] < nx and 0 <= target[1] < ny):
        raise ValueError(f"the target position {target[0]:g}, {target[1]:g} is outside the image ({nx} × {ny} px)")
    for i, xy in enumerate(comps or (), 1):
        if not (0 <= xy[0] < nx and 0 <= xy[1] < ny):
            raise ValueError(f"comparison star {i} at {xy[0]:g}, {xy[1]:g} is outside the image ({nx} × {ny} px)")


@step(
    "photometry.light_curve",
    inputs=("images", "target_xy", "comps_xy"),
    outputs=("light_curve",),
    optional=("coord", "extra_xy", "ref_image", "stars_sky"),
    r_ap=4.0,
    r_in=10.0,
    r_out=16.0,
    gain=None,
    auto_apertures=False,
    follow_seeing=False,
    psf=False,
    aperture_m=None,
    camera=None,
    sky_method="median",
    fixed=(),
    header_time="auto",
    shutter_delay=0.0,
    apertures=(),
    remove_neighbours=False,
    centring="auto",
    track_stars=(),
    combine=1,
    aperture_shape=None,
)
def light_curve_step(inputs, params, ctx):
    """Differential aperture photometry of the target against the comparison stars on every frame: the light curve
    and its table."""
    images = timing.chronological(inputs["images"])
    ref = inputs.get("ref_image") or images[0]  # the positions belong to the frame they were marked on
    images, inputs, ref = combined(images, inputs, ref, params.get("combine") or 1, ctx)  # PHO-42
    inputs = placed_by_sky(inputs, images, ref)  # a recipe on another night: by the sky (PHO-20)
    ref = inputs.get("ref_image") or images[0]
    _check_positions(ref, inputs["target_xy"], inputs["comps_xy"])
    lc = light_curve(
        images,
        inputs["target_xy"],
        inputs["comps_xy"],
        params["r_ap"],
        params["r_in"],
        params["r_out"],
        coord=inputs.get("coord"),
        gain=params["gain"],
        ctx=ctx,
        auto=params["auto_apertures"],
        follow_seeing=params["follow_seeing"],
        extra_xy=inputs.get("extra_xy") or (),
        psf=params["psf"],
        aperture_m=params["aperture_m"],
        ref_path=ref,
        camera=params.get("camera"),
        sky_method=params.get("sky_method", "median"),
        fixed=tuple(params.get("fixed") or ()),
        header_time=params.get("header_time", "auto"),
        shutter_delay=params.get("shutter_delay", 0.0),
        apertures=tuple(params.get("apertures") or ()),
        remove_neighbours=bool(params.get("remove_neighbours")),
        centring=params.get("centring", "auto"),
        track_stars=params.get("track_stars") or (),
        shape=params.get("aperture_shape"),
    )
    return {"light_curve": lc}


@step(
    "photometry.multifilter",
    inputs=("images", "target_xy", "comps_xy"),
    outputs=("curves", "colour"),
    optional=("coord", "extra_xy", "ref_image"),
    **REGISTRY["photometry.light_curve"].defaults,
    t_ab=None,
    comp_colour=None,
)
def multifilter_step(inputs, params, ctx):
    """A mixed sequence of filters (plans/photometry.md item 11): a light curve per filter, with the same stars,
    radii and options, and the colour-index curve of the bluer pair (multifilter.colour_curve)."""
    from .multifilter import by_filter, colour_curve, colour_pair

    groups = {f: g for f, g in by_filter(inputs["images"]).items() if len(g) >= 2}
    if len(groups) < 2:
        raise ValueError("a colour needs images in two filters")
    ref = inputs.get("ref_image") or timing.chronological(inputs["images"])[0]
    curves = {}
    for k, (f, paths) in enumerate(groups.items()):
        ctx.progress(k / len(groups), "photometry")
        lc = light_curve_step(dict(inputs) | {"images": paths, "ref_image": ref}, params, ctx)
        curves[f] = lc["light_curve"] | {"filter": f}
    a, b = colour_pair(list(curves))
    colour = colour_curve(curves[a], curves[b], t_ab=params.get("t_ab"), comp_colour=params.get("comp_colour"))
    return {"curves": curves, "colour": colour}


@step(
    "photometry.varfind",
    inputs=("images",),
    outputs=("field", "variability"),
    max_stars=300,
    method="aperture",
    threshold=3.0,
)
def varfind_step(inputs, params, ctx):
    """Every star of the field on every frame, and which of them vary (fieldstars.py)."""
    from .fieldstars import field_photometry, variability

    field = field_photometry(inputs["images"], params["max_stars"], params["method"], ctx)
    return {"field": field, "variability": variability(field["mag"], field["err"], params["threshold"])}


@step(
    "photometry.apertures", inputs=("images", "target_xy"), outputs=("apertures",), optional=("comps_xy",), rule="snr"
)
def apertures_step(inputs, params, ctx):
    """Aperture and sky annulus from the stars' own profiles on the first frame given (see choose_apertures). rule
    "snr": the best signal-to-noise, then the steadiest light curve of a series; "aij": AstroImageJ's radii."""
    from ..calibration.masters import load
    from .aperture import choose_apertures

    first = inputs["images"][0]  # the frame the stars were marked on (the Photometry page sends it first)
    _check_positions(first, inputs["target_xy"], inputs.get("comps_xy"))
    data, header = load(first)
    ctx.progress(0.2, "photometry")
    gain = get(header, "EGAIN", "GAIN", default=1.0) or 1.0
    stars = [inputs["target_xy"], *(inputs.get("comps_xy") or [])]
    a = choose_apertures(data, stars, gain, params.get("rule", "snr"))
    a["rule"] = params.get("rule", "snr")
    if (
        a["rule"] == "snr" and len(stars) > 1 and len(inputs["images"]) >= 5
    ):  # a series: the radius that gives the steadiest light curve
        from .lightcurve import aperture_scan

        try:
            scan = aperture_scan(inputs["images"], stars, a["fwhm"], gain, r_in=a["r_in"], ctx=ctx)
        except ValueError:  # too few frames with every star: the profile's choice stands
            scan = None
        if scan:
            a |= {"r_ap": round(scan["best"], 2), "r_in": round(scan["r_in"], 2), "r_out": round(scan["r_out"], 2)}
            a["encircled_at_aperture"] = float(np.interp(scan["best"], a["radii"], a["encircled"]))
            a["scan"] = scan
    return {"apertures": a}


@step(
    "timeseries.minimum", inputs=("light_curve",), outputs=("minimum",), method="kvw", t0=None, period=None,
    detrend_with=(),
)  # fmt: skip
def minimum_step(inputs, params, ctx):
    """Time of minimum of a light curve; with t0 and period also epoch and O-C (days). detrend_with: quantities
    (airmass, fwhm, sky, x, y) fitted together with the trapezoid, on the light curve before any detrending
    (plans/photometry.md item 16)."""
    from ..timeseries.minima import dips, each_minimum
    from ..timeseries.timing_methods import time_minimum

    lc = inputs["light_curve"]
    t, y = np.asarray(lc["time"]), np.asarray(lc["rel_flux"])
    err = np.asarray(lc["rel_flux_err"]) if lc.get("rel_flux_err") else None
    y_norm = y / np.median(y)
    if params["t0"] is not None and params["period"] and np.ptp(t) > 0.6 * params["period"]:

        def timer(tw, yw):  # one minimum in its window
            if params["method"] not in ("kvw", "trapezoid"):  # OC-2's other methods
                r = time_minimum(tw, yw, method=params["method"], bootstrap=100)
                return r.t_min, r.error
            if params["method"] == "kvw":
                tm, s_kvw, s_boot = kwee_van_woerden(tw, yw)
                return tm, float(np.nanmax([s_kvw, s_boot]))
            fit = trapezoid_fit(tw, yw)
            return fit["t0"], fit["t0_err"]

        found, skipped = each_minimum(t, y_norm, params["t0"], params["period"], timer)
        if not found:
            raise ValueError(
                "no whole eclipse at the times predicted by T0 and the period: check T0, the period and the time scale"
            )
        minima = []
        for tm, e, k in found:  # a secondary minimum is half a cycle on: its epoch ends in .5
            half = 0.5 * params["period"] if k == "II" else 0.0
            n, oc = o_minus_c([tm - half], params["t0"], params["period"])
            epoch = int(n[0]) + (0.5 if k == "II" else 0)
            minima.append({"time": tm, "error": e, "kind": k, "epoch": epoch, "o_minus_c": float(oc[0])})
            minima[-1]["method"] = params["method"]
        for m in minima:
            m["time_scale"] = lc.get("time_scale")
        return {"minimum": minima[0] | {"minima": minima, "skipped": skipped}}
    n = 1 if params["t0"] is not None and params["period"] else dips(t, y_norm)  # the ephemeris says which one
    if n == 0:  # a fit to noise gives a time that means nothing
        raise ValueError("no eclipse or transit stands out of the noise in this light curve: do the frames cover it?")
    if n > 1:  # one fit through several eclipses gives a meaningless time
        raise ValueError(
            f"the light curve shows {n} eclipses: give T0 and the period (e.g. from the period search) to time each one"
        )
    if params["method"] == "kvw":
        tm, s_kvw, s_boot = kwee_van_woerden(t, y_norm)
        out = {"time": tm, "error": float(np.nanmax([s_kvw, s_boot])), "method": "kvw"}
    elif params["method"] != "trapezoid":  # OC-2: the three errors and the quality of the timing beside the time
        r = time_minimum(t, y_norm, None if err is None else err / np.median(y), method=params["method"])
        out = {"time": r.t_min, "error": r.error, "method": r.method, "errors": r.errors, "quality": r.quality,
               "notes": r.notes}  # fmt: skip
    else:
        cov = None
        if params.get("detrend_with"):
            from .differential import covariates

            have = covariates(lc)
            missing = [k for k in params["detrend_with"] if k not in have]
            if missing:
                raise ValueError("not in this light curve: {missing}".format(missing=", ".join(missing)))
            cov = {k: have[k] for k in params["detrend_with"]}
        fit = trapezoid_fit(t, y_norm, None if err is None else err / np.median(y), cov)
        out = {
            "time": fit["t0"],
            "error": fit["t0_err"],
            "method": "trapezoid",
            "depth": fit["depth"],
            "depth_err": fit["depth_err"],
            "duration": fit["t14"],
            "bic": fit["bic"],
            "detrended_with": fit["coefficients"],
        }
    out["time_scale"] = lc.get("time_scale")
    if params["t0"] is not None and params["period"]:
        epoch, oc = o_minus_c([out["time"]], params["t0"], params["period"])
        out |= {"epoch": int(epoch[0]), "o_minus_c": float(oc[0])}
    return {"minimum": out}


@step(
    "timeseries.period",
    inputs=("time", "flux"),
    outputs=("periods", "power", "best", "warnings", "peaks", "fap"),
    optional=("err",),
    method="lomb-scargle",
    p_min=0.05,
    p_max=None,
)
def period_step(inputs, params, ctx):
    """Period search of a light curve (Lomb-Scargle, BLS, PDM, ANOVA, generalised LS, multi-harmonic AoV,
    conditional entropy or string length): the periodogram and the best periods."""
    from ..timeseries import period
    from ..timeseries.fourier import anova

    t, y = np.asarray(inputs["time"], float), np.asarray(inputs["flux"], float)
    err = inputs.get("err")
    e = np.asarray(err, float) if err is not None and len(err) == len(t) else None
    ok = np.isfinite(t) & np.isfinite(y) & (np.isfinite(e) & (e > 0) if e is not None else True)
    t, y = t[ok], y[ok]
    e = e[ok] if e is not None else None
    p_max = params["p_max"] or np.ptp(t) / 2
    if p_max <= params["p_min"]:  # a period needs at least two cycles in the data
        raise ValueError(f"the light curve spans {24 * np.ptp(t):.2g} h: too short to search for periods")
    from ..timeseries import methods

    funcs = {"lomb-scargle": period.lomb_scargle, "bls": period.bls, "pdm": period.pdm, "anova": anova,
             "gls": methods.gls, "aovmh": methods.aovmh, "conditional_entropy": methods.conditional_entropy,
             "string_length": methods.string_length}  # fmt: skip
    func = funcs[params["method"]]
    ctx.progress(0.0, params["method"])
    weighted = {"err": e} if e is not None and params["method"] in ("lomb-scargle", "bls", "gls", "aovmh") else {}
    periods, power, best = func(t, y, p_min=params["p_min"], p_max=p_max, **weighted)
    from ..timeseries import significance

    peaks = significance.peak_table(periods, power, t)  # PER-4: the aliases and harmonics of each peak
    fap = None
    if params["method"] in ("lomb-scargle", "gls") and len(power):  # Baluev's analytic bound for LS-type power
        fap = significance.fap_baluev(t, y, e, float(np.max(power)), 1 / p_max, 1 / params["p_min"])
    return {"periods": np.asarray(periods).tolist(), "power": np.asarray(power).tolist(), "best": best,
            "warnings": period_warnings(np.ptp(t), params["p_min"], p_max, best, power), "peaks": peaks,
            "fap": fap}  # fmt: skip


def period_warnings(span, p_min, p_max, best, power=()):
    """Why the best period may not be real (PLAN.md R5): the data are too short for it, or it sits at the edge of
    the range searched, where the true peak may lie outside."""
    if span < 2 * p_min:
        return [
            f"the light curve spans {24 * span:.3g} h, less than two cycles of the shortest period searched "
            f"({p_min:g} d): no period in this range can be found; observe longer and search again"
        ]
    out = []
    if best > span / 2:
        out.append(
            f"the best period ({best:.6g} d) is longer than half the time the light curve spans ({span:.3g} d): "
            "fewer than two cycles were seen"
        )
    power = np.asarray(power, float)
    # the highest point is the first or last trial: the peak may lie outside the range
    edge = len(power) > 2 and np.isfinite(power).any() and np.nanargmax(power) in (0, len(power) - 1)
    if edge or not p_min <= best <= p_max:
        out.append(f"the best period is at the edge of the range searched ({p_min:g} to {p_max:g} d): widen the range")
    return out


@step(
    "photometry.suggest_comparisons",
    inputs=("images", "target_xy"),
    outputs=("comps_xy", "catalogue"),
    optional=("field",),
    r_out=16.0,
    n=4,
    rules=None,
)
def suggest_step(inputs, params, ctx):
    """Comparison stars around the target. With the field identified on the marked frame (photometry.identify_field)
    they come from Gaia, as Siril chooses them (field.comparison_stars); "catalogue" then holds the target's colour
    and whether the stars share it. Without it, from the image (aperture.suggest_comparisons)."""
    from ..calibration.masters import load
    from ..calibration.stacking import align_offsets
    from ..io.inspect import saturation_level
    from .aperture import suggest_comparisons

    images = [inputs["images"][0], *timing.chronological(inputs["images"][1:])]  # the marked frame first
    _check_positions(images[0], inputs["target_xy"])
    data, header = load(images[0])
    # stars must stay in the frame for the whole series: a tenth of a binned pixel is plenty for that check
    offsets = np.asarray(align_offsets(images, ctx, binning=2 if data.size > 4_000_000 else 1))
    if inputs.get("field") and params.get("rules") is not None:
        from .comprules import suggest

        return suggest(images, offsets, inputs, params, data, header)
    if inputs.get("field"):
        from .field import comparison_stars

        drift = int(np.ceil(np.abs(offsets).max())) if len(offsets) else 0
        out = comparison_stars(
            inputs["field"], inputs["target_xy"], data, saturation_level(header, data), n=params["n"],
            r_out=params["r_out"], margin=60 + drift,
        )  # fmt: skip
        return {"comps_xy": [[x, y] for x, y, *_ in out["stars"]], "catalogue": out}
    picks = suggest_comparisons(data, inputs["target_xy"], params["r_out"], n=params["n"], r_in=None, offsets=offsets)
    return {"comps_xy": [list(p) for p in picks], "catalogue": None}


@step(
    "photometry.identify_field",
    inputs=("image",),
    outputs=("field",),
    params=[
        P("fresh", "bool", False, label=QT_TRANSLATE_NOOP("Steps", "Ask the catalogues again"),
          help=QT_TRANSLATE_NOOP("Steps", "Not the answers saved from an earlier look-up")),
    ],
)  # fmt: skip
def identify_field_step(inputs, params, ctx):
    """The frame solved against Gaia (no solver to install), the VSX variable stars in it, and whether the OBJECT of
    its header is in it (field.identify). fresh: the catalogues asked again, not read from the saved answers."""
    from contextlib import nullcontext

    from ..services.cache import fresh
    from .field import identify

    with fresh() if params.get("fresh") else nullcontext():
        return {"field": identify(readable(inputs["image"]), ctx)}


@step(
    "photometry.quality",
    inputs=("images",),
    outputs=("quality", "good"),
    fwhm_factor=1.5,
    star_fraction=0.5,
    background_factor=3.0,
)
def quality_step(inputs, params, ctx):
    """FWHM, background, star count of every frame; "good" lists the frames that pass (for photometry/stacks)."""
    import numpy as np

    from ..calibration import stacking
    from ..engine.parallel import pmap, workers
    from .quality import judge, measure_run

    paths = timing.chronological(inputs["images"])
    # runs of consecutive frames on every core (threads gave 1.7x: decompression holds the GIL); each run also
    # measures the shifts between its frames, kept for the comparison suggestion and the light curve
    n = max(1, min(4 * workers(), len(paths) // 8))
    edges = np.linspace(0, len(paths), n + 1).round().astype(int)
    runs = [paths[max(a - 1, 0) : b] for a, b in zip(edges[:-1], edges[1:], strict=True) if b > a]
    rows, shifts, binning = [], [], 1
    for k, (r, run_binning, s) in enumerate(pmap(measure_run, runs, ctx, "quality", min_items=2)):
        rows += r[1:] if k else r  # a run's first frame is the last one of the run before
        shifts += s
        binning = run_binning
    if len(paths) > 1:
        keys = stacking._pair_keys(paths, binning)
        found = {k: [float(x), float(y)] for k, (x, y) in zip(keys, shifts, strict=True)}
        stacking._save_shifts(stacking._shift_cache(), found)
    judge(rows, params["fwhm_factor"], params["star_fraction"], params["background_factor"])
    return {"quality": rows, "good": [r["file"] for r in rows if r["good"]]}


@step("photometry.catalog", inputs=("image", "comps_xy", "target_xy"), outputs=("catalog",), filter="V", source="auto")
def catalog_step(inputs, params, ctx):
    """Catalogue magnitudes of the comparison stars and the target, found by the image's WCS: source "auto" (Gaia
    GSPC, APASS, the Gaia polynomials; catalog.star_magnitude) or "aavso" (the field's AAVSO sequence and chart)."""
    from astropy.wcs import WCS

    from ..calibration.masters import load
    from . import catalog

    _, header = load(inputs["image"])
    wcs = WCS(header)
    if not wcs.has_celestial:
        raise ValueError("the first image has no sky coordinates: plate-solve it first (Image menu)")
    stars = [inputs["target_xy"], *inputs["comps_xy"]]
    if params["source"] == "aavso":
        return {"catalog": _aavso_catalog(wcs, stars, params["filter"])}
    found = []
    for i, (x, y) in enumerate(stars):
        ctx.check()
        ctx.progress(i / len(stars), "catalogue")
        entry = catalog.vizier_fetch(wcs.pixel_to_world(x, y))
        found.append(catalog.star_magnitude(entry, params["filter"], apass_first=params["source"] == "apass"))
    return {"catalog": {"target": found[0], "comps": found[1:], "filter": params["filter"]}}


def _aavso_catalog(wcs, stars, filt):
    """The sequence stars at the marked stars (None where the sequence has none in the band), with the chart id."""
    import numpy as np

    from ..services import aavso_vsp

    xy = np.asarray(stars, float)
    ra, dec = wcs.celestial.pixel_to_world_values(xy[:, 0], xy[:, 1])
    reach = 60 * np.max(np.hypot((ra - ra[0]) * np.cos(np.radians(dec[0])), dec - dec[0]))
    seq = aavso_vsp.sequence(float(ra[0]), float(dec[0]), fov=max(10.0, 2.2 * reach + 2), maglimit=17.0)
    points = list(zip(ra, dec, strict=True))
    found, b, v = (aavso_vsp.sequence_magnitudes(seq, points, band) for band in (filt, "B", "V"))
    out = [f and {"mag": f["mag"], "err": f["err"] or 0.03, "source": f"AAVSO {seq['chart']} {f['label']}",
                  "colour": bi["mag"] - vi["mag"] if bi and vi else None}
           for f, bi, vi in zip(found, b, v, strict=True)]  # fmt: skip
    return {"target": None, "comps": out[1:], "filter": filt, "chart": seq["chart"]}


@step("timeseries.mission_lc", inputs=("target", "folder"), outputs=("light_curve",), mission="TESS", flux="PDCSAP")
def mission_lc_step(inputs, params, ctx):
    """TESS / Kepler / K2 pipeline light curves of a target from MAST, joined (needs the internet)."""
    from ..timeseries import archive

    ctx.progress(0.05, "MAST")
    paths = archive.download(inputs["target"], params["mission"], inputs["folder"])
    curves = []
    for i, p in enumerate(paths):
        ctx.check()
        ctx.progress(0.5 + 0.5 * i / len(paths), "reading")
        curves.append(archive.read_mission_lc(p, params["flux"]))
    return {"light_curve": archive.join(curves)}


@step("astrometry.moving", inputs=("images", "first_xy", "last_xy"), outputs=("positions", "unsolved"), box=11)
def moving_step(inputs, params, ctx):
    """Positions of a moving object on plate-solved frames (marked on the first and the last frame)."""
    from astropy.io import fits
    from astropy.wcs import WCS

    from ..engine.builtin import solved_copy
    from ..io.fits import find_image_hdu
    from .moving import track

    paths, unsolved = [], []
    for n, p in enumerate(inputs["images"]):  # frames without sky coordinates are plate-solved first
        with fits.open(readable(p)) as hdul:
            solved = WCS(hdul[find_image_hdu(hdul)].header).has_celestial
        if solved:
            paths.append(str(p))
            continue
        ctx.progress(0.8 * n / len(inputs["images"]), "plate solving")
        try:
            paths.append(str(solved_copy(p)))
        except Exception:  # a frame the solver cannot solve (clouds, trails) is left out, the others count
            unsolved.append(str(p))
    if len(paths) < 2:
        raise ValueError("the image has no sky coordinates: plate-solve it first (Image menu)")
    ctx.progress(0.9, "astrometry")
    return {"positions": track(paths, inputs["first_xy"], inputs["last_xy"], params["box"]), "unsolved": unsolved}


@step(
    "photometry.transformation",
    inputs=("image_a", "image_b"),
    outputs=("transformation", "stars"),
    band_a="B",
    band_b="V",
)
def transformation_step(inputs, params, ctx):
    """Transformation coefficients from two plate-solved images of a standard field (catalogue from VizieR)."""
    from .coefficients import standard_stars, transformation

    ctx.progress(0.1, "photometry")
    stars = standard_stars(inputs["image_a"], inputs["image_b"], params["band_a"], params["band_b"])
    ctx.progress(0.8, "catalogue")
    coef = transformation(
        stars["cat_a"], stars["cat_b"], stars["inst_a"], stars["inst_b"], (params["band_a"], params["band_b"])
    )
    return {"transformation": coef, "stars": stars}


# --- the settings described (AUT-1): kind, unit, range, label and help -------------------------------------------
describe(
    "photometry.varfind",
    P(
        "max_stars",
        "int",
        300,
        min=1,
        label=QT_TRANSLATE_NOOP("Steps", "Most stars"),
        help=QT_TRANSLATE_NOOP("Steps", "The brightest stars of the field that are measured"),
    ),
    P(
        "method",
        "choice",
        "aperture",
        choices=("aperture", "psf"),
        label=QT_TRANSLATE_NOOP("Steps", "Method"),
        help=QT_TRANSLATE_NOOP("Steps", "Aperture photometry, or PSF fitting for crowded fields"),
    ),
    P(
        "threshold",
        "float",
        3.0,
        min=0.0,
        label=QT_TRANSLATE_NOOP("Steps", "Threshold"),
        help=QT_TRANSLATE_NOOP("Steps", "How many times its expected scatter a star must vary to be listed"),
    ),
)
describe(
    "photometry.apertures",
    P(
        "rule",
        "choice",
        "snr",
        choices=("snr", "aij"),
        label=QT_TRANSLATE_NOOP("Steps", "Rule"),
        help=QT_TRANSLATE_NOOP(
            "Steps", "snr: the radius of the best signal-to-noise; aij: AstroImageJ's, from the FWHM"
        ),
    ),
)
describe(
    "timeseries.minimum",
    P(
        "method",
        "choice",
        "kvw",
        choices=("kvw", "trapezoid", "mikulasek", "gaussian", "lorentzian", "bisector", "polynomial"),
        label=QT_TRANSLATE_NOOP("Steps", "Method"),
        help=QT_TRANSLATE_NOOP(
            "Steps",
            "Kwee–van Woerden for eclipses, a trapezoid for transits; or Mikulášek's eclipse model, a Gaussian, a "
            "Lorentzian, the bisector or a polynomial (each with its three errors)",
        ),
    ),
    P(
        "t0",
        "time",
        None,
        unit="d",
        label=QT_TRANSLATE_NOOP("Steps", "Reference T0"),
        help=QT_TRANSLATE_NOOP("Steps", "With the period: every eclipse in the curve gets its own time"),
    ),
    P(
        "period",
        "float",
        None,
        unit="d",
        min=0.0,
        label=QT_TRANSLATE_NOOP("Steps", "Period"),
        help=QT_TRANSLATE_NOOP("Steps", "Period of the ephemeris used to count the cycles"),
    ),
    P(
        "detrend_with",
        "table",
        (),
        label=QT_TRANSLATE_NOOP("Steps", "Detrend against"),
        help=QT_TRANSLATE_NOOP("Steps", "Airmass, sky, position… fitted with the transit (trapezoid only)"),
        advanced=True,
    ),
)
describe(
    "timeseries.period",
    P(
        "method",
        "choice",
        "lomb-scargle",
        choices=("lomb-scargle", "bls", "pdm", "anova", "gls", "aovmh", "conditional_entropy", "string_length"),
        label=QT_TRANSLATE_NOOP("Steps", "Method"),
        help=QT_TRANSLATE_NOOP(
            "Steps",
            "Pulsators: Lomb–Scargle or the generalised one; transits: box least squares; eclipsing binaries: "
            "multi-harmonic AoV, phase dispersion or string length; sparse survey data: conditional entropy",
        ),
    ),
    P(
        "p_min",
        "float",
        0.05,
        unit="d",
        min=0.0,
        label=QT_TRANSLATE_NOOP("Steps", "Shortest period"),
        help=QT_TRANSLATE_NOOP("Steps", "The search starts here"),
    ),
    P(
        "p_max",
        "float",
        None,
        unit="d",
        min=0.0,
        label=QT_TRANSLATE_NOOP("Steps", "Longest period"),
        help=QT_TRANSLATE_NOOP("Steps", "Empty: half the time span"),
    ),
)
describe(
    "photometry.suggest_comparisons",
    P(
        "r_out",
        "float",
        16.0,
        unit="px",
        min=0.0,
        label=QT_TRANSLATE_NOOP("Steps", "Outer sky radius"),
        help=QT_TRANSLATE_NOOP("Steps", "No other star may fall inside it"),
    ),
    P(
        "n",
        "int",
        4,
        min=1,
        max=50,
        label=QT_TRANSLATE_NOOP("Steps", "Comparison stars"),
        help=QT_TRANSLATE_NOOP("Steps", "How many to suggest"),
    ),
    P(
        "rules",
        "object",
        None,
        label=QT_TRANSLATE_NOOP("Steps", "Comparison-star rules"),
        help=QT_TRANSLATE_NOOP("Steps", "The rules' settings; each star left out is given its reason (with a field)"),
    ),
)
describe(
    "photometry.quality",
    P(
        "fwhm_factor",
        "float",
        1.5,
        min=1.0,
        label=QT_TRANSLATE_NOOP("Steps", "FWHM limit"),
        help=QT_TRANSLATE_NOOP("Steps", "A frame whose FWHM exceeds this times the median is bad (focus, trails)"),
    ),
    P(
        "star_fraction",
        "float",
        0.5,
        min=0.0,
        max=1.0,
        label=QT_TRANSLATE_NOOP("Steps", "Star fraction"),
        help=QT_TRANSLATE_NOOP("Steps", "A frame that finds fewer than this share of the stars is bad (clouds)"),
    ),
    P(
        "background_factor",
        "float",
        3.0,
        min=1.0,
        label=QT_TRANSLATE_NOOP("Steps", "Sky limit"),
        help=QT_TRANSLATE_NOOP("Steps", "A frame whose sky exceeds this times the median is bad (Moon, twilight)"),
    ),
)
describe(
    "photometry.transformation",
    P(
        "band_a",
        "band",
        "B",
        label=QT_TRANSLATE_NOOP("Steps", "First band"),
        help=QT_TRANSLATE_NOOP("Steps", "The filter of the first image"),
    ),
    P(
        "band_b",
        "band",
        "V",
        label=QT_TRANSLATE_NOOP("Steps", "Second band"),
        help=QT_TRANSLATE_NOOP("Steps", "The filter of the second image"),
    ),
)
describe(
    "photometry.catalog",
    P(
        "filter",
        "band",
        "V",
        label=QT_TRANSLATE_NOOP("Steps", "Band"),
        help=QT_TRANSLATE_NOOP("Steps", "The band of the standard magnitudes"),
    ),
    P(
        "source",
        "choice",
        "auto",
        choices=("auto", "apass", "aavso"),
        label=QT_TRANSLATE_NOOP("Steps", "Magnitudes from"),
        help=QT_TRANSLATE_NOOP(
            "Steps", "auto: Gaia GSPC, APASS, Gaia colours; apass: APASS first; aavso: the field's AAVSO sequence"
        ),
    ),
)
describe(
    "timeseries.mission_lc",
    P(
        "mission",
        "choice",
        "TESS",
        choices=("TESS", "Kepler", "K2"),
        label=QT_TRANSLATE_NOOP("Steps", "Mission"),
        help=QT_TRANSLATE_NOOP("Steps", "The space telescope whose light curves are fetched"),
    ),
    P(
        "flux",
        "text",
        "PDCSAP",
        label=QT_TRANSLATE_NOOP("Steps", "Flux"),
        help=QT_TRANSLATE_NOOP("Steps", "PDCSAP: corrected for the spacecraft; SAP: as measured"),
    ),
)

describe("photometry.light_curve", *_MEASURE)
describe(
    "photometry.multifilter",
    *_MEASURE,
    P(
        "t_ab",
        "float",
        None,
        label=QT_TRANSLATE_NOOP("Steps", "Colour coefficient"),
        help=QT_TRANSLATE_NOOP("Steps", "T_ab of the transformation; with the comparison colour, a standard colour"),
    ),
    P(
        "comp_colour",
        "float",
        None,
        unit="mag",
        label=QT_TRANSLATE_NOOP("Steps", "Comparison colour"),
        help=QT_TRANSLATE_NOOP("Steps", "The comparison ensemble's catalogue colour"),
    ),
)

from . import fit_steps, polarimetry_step  # noqa: E402, F401  (register photometry.transit_fit, .polarimetry)
