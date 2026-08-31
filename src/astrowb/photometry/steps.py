"""Photometry and timing as engine steps."""

import numpy as np

from .. import timing
from ..engine.steps import step
from ..hdr import get, number
from ..io.lzw import readable
from ..timeseries.minima import kwee_van_woerden, o_minus_c, trapezoid_fit
from .lightcurve import light_curve


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
    optional=("coord", "extra_xy", "ref_image"),
    r_ap=4.0,
    r_in=10.0,
    r_out=16.0,
    gain=None,
    auto_apertures=False,
    follow_seeing=False,
    psf=False,
    aperture_m=None,
)
def light_curve_step(inputs, params, ctx):
    images = timing.chronological(inputs["images"])
    ref = inputs.get("ref_image") or images[0]  # the positions belong to the frame they were marked on
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
    )
    return {"light_curve": lc}


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


@step("photometry.apertures", inputs=("images", "target_xy"), outputs=("apertures",), optional=("comps_xy",))
def apertures_step(inputs, params, ctx):
    """Aperture and sky annulus from the stars' own profiles on the first frame given (see choose_apertures)."""
    from ..calibration.masters import load
    from .aperture import choose_apertures

    first = inputs["images"][0]  # the frame the stars were marked on (the Photometry page sends it first)
    _check_positions(first, inputs["target_xy"], inputs.get("comps_xy"))
    data, header = load(first)
    ctx.progress(0.2, "photometry")
    gain = get(header, "EGAIN", "GAIN", default=1.0) or 1.0
    stars = [inputs["target_xy"], *(inputs.get("comps_xy") or [])]
    a = choose_apertures(data, stars, gain)
    if len(stars) > 1 and len(inputs["images"]) >= 5:  # a series: the radius that gives the steadiest light curve
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


@step("timeseries.minimum", inputs=("light_curve",), outputs=("minimum",), method="kvw", t0=None, period=None)
def minimum_step(inputs, params, ctx):
    """Time of minimum of a light curve; with t0 and period also epoch and O-C (days)."""
    from ..timeseries.minima import dips, each_minimum

    lc = inputs["light_curve"]
    t, y = np.asarray(lc["time"]), np.asarray(lc["rel_flux"])
    err = np.asarray(lc["rel_flux_err"]) if lc.get("rel_flux_err") else None
    y_norm = y / np.median(y)
    if params["t0"] is not None and params["period"] and np.ptp(t) > 0.6 * params["period"]:

        def timer(tw, yw):  # one minimum in its window
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
    else:
        fit = trapezoid_fit(t, y_norm, None if err is None else err / np.median(y))
        out = {
            "time": fit["t0"],
            "error": fit["t0_err"],
            "method": "trapezoid",
            "depth": fit["depth"],
            "duration": fit["t14"],
        }
    out["time_scale"] = lc.get("time_scale")
    if params["t0"] is not None and params["period"]:
        epoch, oc = o_minus_c([out["time"]], params["t0"], params["period"])
        out |= {"epoch": int(epoch[0]), "o_minus_c": float(oc[0])}
    return {"minimum": out}


@step(
    "timeseries.period",
    inputs=("time", "flux"),
    outputs=("periods", "power", "best"),
    optional=("err",),
    method="lomb-scargle",
    p_min=0.05,
    p_max=None,
)
def period_step(inputs, params, ctx):
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
    funcs = {"lomb-scargle": period.lomb_scargle, "bls": period.bls, "pdm": period.pdm, "anova": anova}
    func = funcs[params["method"]]
    ctx.progress(0.0, params["method"])
    weighted = {"err": e} if e is not None and params["method"] in ("lomb-scargle", "bls") else {}  # 1/σ² weights
    periods, power, best = func(t, y, p_min=params["p_min"], p_max=p_max, **weighted)
    return {"periods": np.asarray(periods).tolist(), "power": np.asarray(power).tolist(), "best": best}


@step(
    "photometry.suggest_comparisons",
    inputs=("images", "target_xy"),
    outputs=("comps_xy", "catalogue"),
    optional=("field",),
    r_out=16.0,
    n=4,
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


@step("photometry.identify_field", inputs=("image",), outputs=("field",))
def identify_field_step(inputs, params, ctx):
    """The frame solved against Gaia (no solver to install), the VSX variable stars in it, and whether the OBJECT of
    its header is in it (field.identify)."""
    from .field import identify

    return {"field": identify(readable(inputs["image"]), ctx)}


ANGLE_KEYS = ("HWPANGLE", "HWP-ANG", "HWP", "RETANG", "RETANGLE", "POLANGLE", "POL-ANG", "WPANGLE", "ANGLE")


@step(
    "photometry.polarimetry",
    inputs=("images", "o_xy", "e_xy"),
    outputs=("polarimetry",),
    r_ap=4.0,
    r_in=10.0,
    r_out=16.0,
    angle_key=None,
    zero_point=0.0,
)
def polarimetry_step(inputs, params, ctx):
    """Dual-beam linear polarimetry: ordinary and extraordinary images of one star on each frame, the
    half-wave-plate angle from the header (or 0, 22.5, 45, 67.5 deg repeating in time order)."""
    from astropy.io import fits

    from . import polarimetry

    paths = timing.chronological(inputs["images"])
    lc = light_curve(
        paths, inputs["o_xy"], [inputs["e_xy"]], params["r_ap"], params["r_in"], params["r_out"], ctx=ctx,
        ref_path=inputs["images"][0],  # the frame the beams were marked on (the Photometry page sends it first)
    )  # fmt: skip
    angles, source = [], None
    for p in paths:
        h = fits.getheader(readable(p))
        keys = [params["angle_key"]] if params["angle_key"] else ANGLE_KEYS
        key = next((k for k in keys if k in h), None)
        if key is None:
            angles = None
            break
        source = key
        angles.append(number(h[key], 0.0))
    if angles is None:
        angles, source = [(22.5 * i) % 90 for i in range(len(paths))], "assumed 0/22.5/45/67.5"
    fo = np.array(lc["target_flux"])
    fe = np.array(lc["comp_flux"])[:, 0]
    # photon + background errors are not kept per beam by light_curve; use the residual scatter
    r = polarimetry.dual_beam(angles, fo, fe, zero_point=params["zero_point"])
    return {
        "polarimetry": r
        | {"angles": angles, "angle_source": source, "f_o": fo.tolist(), "f_e": fe.tolist(), "files": lc["file"]}
    }


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


@step("photometry.catalog", inputs=("image", "comps_xy", "target_xy"), outputs=("catalog",), filter="V")
def catalog_step(inputs, params, ctx):
    """Catalogue magnitudes (APASS / Gaia) of the comparison stars and the target, found by the image's WCS."""
    from astropy.wcs import WCS

    from ..calibration.masters import load
    from . import catalog

    _, header = load(inputs["image"])
    wcs = WCS(header)
    if not wcs.has_celestial:
        raise ValueError("the first image has no sky coordinates: plate-solve it first (Image menu)")
    stars = [inputs["target_xy"], *inputs["comps_xy"]]
    found = []
    for i, (x, y) in enumerate(stars):
        ctx.check()
        ctx.progress(i / len(stars), "catalogue")
        entry = catalog.vizier_fetch(wcs.pixel_to_world(x, y))
        found.append(catalog.star_magnitude(entry, params["filter"]))
    return {"catalog": {"target": found[0], "comps": found[1:], "filter": params["filter"]}}


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
