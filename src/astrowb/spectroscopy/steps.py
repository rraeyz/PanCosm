"""Spectroscopy as engine steps."""

import re
from pathlib import Path

import numpy as np

from .. import timing
from ..calibration.masters import load
from ..engine.steps import step
from ..hdr import get, number
from . import bf, echelle, longslit, orbit, rv, sb2, spectrum_io, telluric, wavecal


def _oriented(data, params):
    """Dispersion along x, wavelength increasing to the right (coude and other spectrographs often
    disperse along the columns, or towards smaller pixel numbers)."""
    if params.get("orientation", "x") == "y":
        data = data.T
    return data[:, ::-1] if params.get("reverse") else data


def looks_extracted(header):
    """True when the header says the spectrum is already extracted (one row per order or a single 1-D spectrum):
    1-D data, an IRAF multispec file (apall / ecidentify input) or an ESO pipeline E2DS (HARPS DRS: one row per
    order it located)."""
    return (
        header.get("NAXIS", 0) == 1
        or "APNUM1" in header
        or "multispec" in str(header.get("WAT0_001", ""))
        or "E2DS" in str(header.get("HIERARCH ESO PRO CATG", "")).upper()
        or header.get("HIERARCH ESO DRS CAL LOC NBO", -1) == header.get("NAXIS2")
    )


def _extracted(path, params, force=None):
    """(flux, error or None, header) of an already-extracted spectrum, one row per order (IRAF apall output, a
    pipeline's e2ds, a 1-D spectrum), or None for a frame still to be extracted. force: the user's choice, None:
    from the header (looks_extracted). Wavelength calibration only, as IRAF identify / ecidentify on apall output."""
    from astropy.io import fits

    from ..io.fits import inherited
    from ..io.lzw import readable

    with fits.open(readable(path)) as hdul:
        i = next(k for k, h in enumerate(hdul) if h.is_image and h.header.get("NAXIS", 0) >= 1)
        header = inherited(hdul, i)
        if not (force if force is not None else looks_extracted(header)):
            return None
        data = np.asarray(hdul[i].data, float)
    err = None
    if data.ndim == 3:  # IRAF bands: spectrum, raw, sky, sigma (BANDIDn)
        band = [str(header.get(f"BANDID{k + 1}", "")).lower() for k in range(data.shape[0])]
        err = next((data[k] for k, b in enumerate(band) if "sigma" in b), None)
        data = data[0]
    flux = np.atleast_2d(data)
    err = None if err is None else np.atleast_2d(err)
    if params.get("reverse"):
        flux, err = flux[:, ::-1], (None if err is None else err[:, ::-1])
    return flux, err, header


def _poisson(flux, header, params):
    # shortcut: photon noise of the counts only (the extraction width is not known); give IRAF's sigma band if needed
    gain = float(params["gain"] or get(header, "EGAIN", "GAIN", default=1.0) or 1.0)
    return np.sqrt(np.clip(flux, 0, None) / gain + (params["read_noise"] / gain) ** 2)


def _thin(profile, n=800):
    """A velocity profile kept at most n points (a CCF of 3000 velocities is drawn as well with 800)."""
    step = max(1, len(profile["v"]) // n)
    return {
        k: (list(np.asarray(v, float)[::step]) if isinstance(v, (list, np.ndarray)) else v) for k, v in profile.items()
    }


def _load(path, params):
    data, header = load(path)
    return _oriented(data, params), header


@step(
    "spectroscopy.reduce",
    inputs=("science",),
    outputs=("spectrum",),
    optional=("arc", "guesses", "output"),
    guess_row=None,
    trace_row=None,  # a brighter spectrum's row whose trace shape is used for a faint one (IRAF apall reference)
    width=10.0,
    sky_offset=15.0,
    sky_width=10.0,
    optimal=True,
    gain=None,
    read_noise=5.0,
    line_list="henear",
    order=5,  # the highest degree; the lines choose (leave-one-out)
    orientation="x",
    reverse=False,
    sky_lines=True,
    exclude=[],
)
def reduce_step(inputs, params, ctx):
    """2-D long-slit/slitless frame (dispersion along x) -> 1-D spectrum; wavelengths from an arc
    when an arc and at least two identified (pixel, wavelength) pairs are given."""
    ext = _extracted(inputs["science"], params)
    if ext is not None:  # an extracted 1-D spectrum: wavelengths only (IRAF identify, dispcor)
        return {"spectrum": _reduce_extracted(ext, inputs, params, ctx)}
    data, header = _load(inputs["science"], params)
    ctx.progress(0.1, "trace")
    try:
        if params["trace_row"] and params["guess_row"]:  # a faint spectrum: the shape of a brighter one, moved to it
            coef = longslit.shifted_trace(data, longslit.trace(data, params["trace_row"]), params["guess_row"])
        else:
            coef = longslit.trace(data, params["guess_row"])
    except ValueError:
        if params["guess_row"] is None:  # the frame turned the other way? (ESO EFOSC2 disperses along y)
            try:
                longslit.trace(data.T)
            except ValueError:
                pass
            else:
                raise ValueError(
                    "the spectrum runs the other way on this frame: change 'Dispersion along' (rows / columns)"
                ) from None
        raise
    gain = float(params["gain"] or get(header, "EGAIN", "GAIN", default=1.0) or 1.0)
    w, so, sw = params["width"], params["sky_offset"], params["sky_width"]
    ctx.progress(0.4, "extraction")
    if params["optimal"]:
        flux, err, sky, _ = longslit.optimal(data, coef, w, so, sw, gain, params["read_noise"])
    else:
        flux, sky = longslit.boxcar(data, coef, w, so, sw)
        err = np.sqrt(np.clip(flux, 0, None) / gain + w * (params["read_noise"] / gain) ** 2)
    arc1d = None
    if inputs.get("arc"):
        ctx.progress(0.7, "arc")
        arc1d = longslit.boxcar(_load(inputs["arc"], params)[0], coef, w, subtract_sky=False)[0]
    return {"spectrum": _wavelengths(flux, err, coef.tolist(), sky, arc1d, header, inputs, params)}


def _reduce_extracted(ext, inputs, params, ctx):
    flux, err, header = ext
    flux = flux[0]
    err = _poisson(flux, header, params) if err is None else err[0]
    arc1d = None
    if inputs.get("arc"):
        ctx.progress(0.7, "arc")
        arc1d = _extracted(inputs["arc"], params, True)[0][0]
        if arc1d.size != flux.size:
            raise ValueError("the arc and the spectrum differ in length: extract the arc with the same aperture")
    return _wavelengths(flux, err, None, None, arc1d, header, inputs, params)


def _wavelengths(flux, err, trace, sky, arc1d, header, inputs, params):
    """The extracted spectrum with its wavelength solution from the arc and the identified lines (IRAF identify,
    dispcor), written to inputs["output"]; sky (beside the trace) gives the zero point from night-sky lines."""
    out = {
        "pixel": np.arange(len(flux)).tolist(),
        "flux": flux.tolist(),
        "error": err.tolist(),
        "trace": trace,
        "wave": None,
        "arc_peaks": [],
        "solution": None,
    }
    if arc1d is not None:
        peaks = wavecal.find_lines(arc1d)
        out["arc"] = arc1d.tolist()
        out["arc_peaks"] = peaks.tolist()
        if params["exclude"]:  # arc lines left out by hand in the residual plot (IRAF identify: d)
            ex = np.asarray(params["exclude"], float)
            peaks = peaks[np.min(np.abs(peaks[:, None] - ex[None, :]), axis=1) > 1.5]
        if inputs.get("guesses") and len(inputs["guesses"]) >= 2:
            # the user's identified wavelengths are lines of the lamp too (e.g. Hg in an HgAr lamp, not in the list)
            catalogue = np.union1d(wavecal.load_line_list(params["line_list"]), [g[1] for g in inputs["guesses"]])
            sol = wavecal.solve(peaks, catalogue, inputs["guesses"], params["order"], n_pixels=len(flux))
            wave = sol(np.arange(len(flux)))
            out["solution"] = {
                "coef": sol.coef.tolist(),
                "rms": sol.rms,
                "n_lines": sol.n_lines,
                "degree": sol.degree,
                # [pixel, wavelength, residual (A)] of every line used, for the residual plot
                "lines": [[float(p), float(w), float(w - sol(p))] for p, w in zip(sol.pixels, sol.waves, strict=True)],
            }
            if params["sky_lines"] and sky is not None:  # the zero point from the night-sky lines (flexure)
                shift, lines = wavecal.sky_shift(wave, np.asarray(sky, float))
                out["sky_shift"] = {"shift": shift, "lines": [list(x) for x in lines]}
                if shift is not None:
                    wave = wave - shift
                    header["WAVSKYSH"] = (round(-shift, 3), "zero point from night-sky lines (Angstrom)")
            out["wave"] = wave.tolist()
    if inputs.get("output") and out["wave"] is not None:
        header["WAVSOLRM"] = (out["solution"]["rms"], "wavelength solution rms (Angstrom)")
        header["WAVSOLN"] = (out["solution"]["n_lines"], "arc lines used")
        out["path"] = spectrum_io.write(inputs["output"], out["wave"], flux, err, header)
    return out


@step(
    "spectroscopy.echelle",
    inputs=("science",),
    outputs=("echelle",),
    optional=("flat", "arc", "guesses", "output"),
    first_order=None,
    order_step=1,
    optimal=True,
    gain=None,
    read_noise=5.0,
    line_list="thar",
    sky_lines=True,
    deg_x=4,
    deg_m=3,
    min_blaze=0.1,
    orientation="x",
    reverse=False,
    sky=True,
    scatter=False,
    exclude=[],
    rows=None,
    extracted=None,
)
def echelle_step(inputs, params, ctx):
    """Echelle / cross-dispersed frame -> orders -> one merged spectrum.

    Orders are traced on the flat (or on the science frame when no flat is given); the flat also
    gives the blaze. With an arc, `first_order` (absolute number of the lowest traced order,
    numbers changing by `order_step` upwards) and identified lines [(order, pixel, wavelength), ...]
    the global 2-D wavelength solution is fitted and the merged spectrum written to `output`.
    sky=False for fibre-fed spectrographs whose orders leave no sky between them. scatter: subtract the
    scattered light (from the gaps between the orders) from the science frame and the flat first. exclude:
    [(order, pixel)] arc lines left out of the wavelength solution by hand. rows: the orders' rows at the central
    column as checked by hand on the Echelle tab (None: found automatically). With an output file the orders
    are also written one by one (<output>_orders.fits: flux, error and wavelength images, one row per order).
    extracted: the science frame (and the flat and arc with it) is already extracted, one row per order (IRAF apall
    output, a pipeline's e2ds): wavelengths only, as IRAF ecidentify; None: from the header (looks_extracted)."""
    ext = _extracted(inputs["science"], params, params["extracted"])
    if ext is not None:
        return {"echelle": _echelle_extracted(ext, inputs, params, ctx)}
    data, header = _load(inputs["science"], params)
    flat = _load(inputs["flat"], params)[0] if inputs.get("flat") else None
    ctx.progress(0.1, "trace orders")
    rows = None if params["rows"] is None else sorted(params["rows"])
    coefs = echelle.trace_orders(flat if flat is not None else data, rows=rows)
    if params["scatter"]:
        data = data - echelle.scattered_light(data, coefs)
        if flat is not None:
            flat = flat - echelle.scattered_light(flat, coefs)
        header["SCATSUB"] = (True, "scattered light subtracted (inter-order fit)")
    gain = float(params["gain"] or get(header, "EGAIN", "GAIN", default=1.0) or 1.0)
    ctx.progress(0.3, "extraction")
    method = "optimal" if params["optimal"] else "boxcar"
    # three times the orders' width: a fibre's whole light without the second fibre beside it (HARPS's ThAr
    # reference lies 17 px from the star in orders 34 px apart; 70 % of the spacing put its lines in the star)
    fwhm = echelle.profile_fwhm(flat if flat is not None else data, coefs)
    width = 3 * fwhm if fwhm else None
    flux, err = echelle.extract(
        data, coefs, width, method=method, subtract_sky=params["sky"], gain=gain, read_noise=params["read_noise"]
    )
    bl = echelle.blaze(echelle.extract(flat, coefs, width, method="boxcar")[0]) if flat is not None else None
    arc = None
    if inputs.get("arc"):
        ctx.progress(0.6, "arc")
        arc = echelle.extract(_load(inputs["arc"], params)[0], coefs, width, method="boxcar", subtract_sky=False)[0]
    skies = None
    if params["sky"] and params["sky_lines"] and arc is not None and inputs.get("guesses"):
        raw = echelle.extract(data, coefs, width, method="boxcar", subtract_sky=False)[0]
        skies = raw - echelle.extract(data, coefs, width, method="boxcar", subtract_sky=True)[0]
    return {"echelle": _echelle_wavelengths(flux, err, bl, coefs, width, arc, skies, header, inputs, params, ctx)}


def _echelle_extracted(ext, inputs, params, ctx):
    flux, err, header = ext
    err = _poisson(flux, header, params) if err is None else err

    def same(path):
        a = _extracted(path, params, True)[0]
        if a.shape != flux.shape:
            raise ValueError(
                f"{Path(path).name} has {a.shape[0]} orders of {a.shape[1]} pixels, the science spectrum "
                f"{flux.shape[0]} of {flux.shape[1]}: extract it with the same apertures"
            )
        return a

    bl = echelle.blaze(same(inputs["flat"])) if inputs.get("flat") else None
    arc = same(inputs["arc"]) if inputs.get("arc") else None
    return _echelle_wavelengths(flux, err, bl, [], None, arc, None, header, inputs, params, ctx)


def _echelle_wavelengths(flux, err, bl, coefs, width, arc, skies, header, inputs, params, ctx):
    """The orders with their 2-D wavelength solution from the arc and the identified lines (IRAF ecidentify), merged
    (dispcor, scombine) and written to inputs["output"]; skies (beside the orders) give the night-sky zero point."""
    nx = flux.shape[1]
    first = params["first_order"]
    orders = None if first is None else [int(first) + params["order_step"] * k for k in range(len(flux))]
    out = {
        "n_orders": len(flux),
        "width": width,  # extraction width (pixels) chosen from the orders' profile
        "orders": orders,
        "flux": flux.tolist(),
        "error": err.tolist(),
        "blaze": None if bl is None else bl.tolist(),
        "traces": [c.tolist() for c in coefs],
        "arc": None,
        "arc_peaks": [],
        "solution": None,
        "wave": None,
        "merged": None,
    }
    if arc is not None:
        peaks = [wavecal.find_lines(a) for a in arc]
        out["arc"], out["arc_peaks"] = arc.tolist(), [p.tolist() for p in peaks]
        if inputs.get("guesses") and orders is not None:
            ctx.progress(0.8, "wavelength solution")
            sol = echelle.solve_2d(
                peaks,
                orders,
                np.union1d(wavecal.load_line_list(params["line_list"]), [g[2] for g in inputs["guesses"]]),
                inputs["guesses"],
                params["deg_x"],
                params["deg_m"],
                nx=nx,
                exclude=params["exclude"],
            )
            waves = sol.wavelengths(nx)
            if skies is not None:  # zero point from the night-sky lines in the inter-order sky
                shift, lines = wavecal.sky_shift_orders(waves, skies)
                out["sky_shift"] = {"shift": shift, "lines": [list(x) for x in lines]}
                if shift is not None:
                    waves = waves - shift
                    header["WAVSKYSH"] = (round(-shift, 4), "zero point from night-sky lines (Angstrom)")
            w, f, e = echelle.merge(waves, flux, err, bl, params["min_blaze"])
            out["wave"] = waves.tolist()
            out["solution"] = {"rms": sol.rms, "n_lines": sol.n_lines, "lines": sol.lines}
            out["merged"] = {"wave": w.tolist(), "flux": f.tolist(), "error": e.tolist()}
            if inputs.get("output"):
                header["WAVSOLRM"] = (sol.rms, "echelle wavelength solution rms (Angstrom)")
                header["WAVSOLN"] = (sol.n_lines, "arc lines used")
                header["NORDERS"] = (len(flux), "orders merged")
                out["path"] = spectrum_io.write(inputs["output"], w, f, e, header)
                out["orders_path"] = _write_orders(inputs["output"], waves, flux, err, orders, header)
    return out


@step(
    "spectroscopy.atmosphere",
    inputs=("spectrum", "cache"),
    outputs=("atmosphere",),
    optional=("grid", "sun"),
    resolution=None,
    vacuum=False,
)
def atmosphere_step(inputs, params, ctx):
    """Teff, log g, [Fe/H], v sin i and RV of an FGK star relative to the Sun (spectroscopy/atmosphere.py).
    grid: a folder of synthetic spectra (else PHOENIX points are downloaded into `cache` as needed); sun: a solar
    spectrum taken with the same spectrograph (else the Kurucz solar atlas, downloaded once); resolution: the
    spectrograph's R = lambda / FWHM."""
    import numpy as np

    from . import atmosphere as atm

    if not params["resolution"]:
        raise ValueError("give the spectrograph's resolution R = lambda / delta lambda")
    R, air = float(params["resolution"]), not params["vacuum"]
    w, f, e, _ = spectrum_io.read(inputs["spectrum"])
    lo, hi = float(np.nanmin(w)) - 30, float(np.nanmax(w)) + 30
    cache = Path(inputs["cache"])

    def progress(frac, text):
        ctx.check()
        ctx.progress(frac, text)

    def grid_of(nodes, frac):
        return atm.Grid.load(atm.download_phoenix(nodes, cache, progress=lambda x, m: progress(frac, m)), lo, hi)

    own = sorted(Path(inputs["grid"]).glob("*.fits")) if inputs.get("grid") else None
    sun_grid = atm.Grid.load(own, lo, hi) if own else grid_of(atm.neighbourhood(*atm.SUN.values()), 0.05)
    progress(0.2, "the Sun")
    if inputs.get("sun"):
        sw, sf, _, _ = spectrum_io.read(inputs["sun"])
        ref = atm.solar_reference(w, sw, sf, sun_grid, R, sun_degraded=True, air=air)
    else:
        sw, sf = atm.download_sun(cache)
        ref = atm.solar_reference(w, sw, sf, sun_grid, R, air=air)
    if own:
        progress(0.6, "fit")
        return {"atmosphere": _atmosphere_out(atm.analyse(w, f, e, sun_grid, R, ref, air=air))}
    progress(0.3, "first estimate")
    first = atm.fit(w, f, e, grid_of(atm.coarse_nodes(), 0.3), R, air=air, mask=ref["mask"])
    centre = (first["teff"], first["logg"], 0.0)
    names, axes = ("teff", "logg", "feh"), atm.phoenix_axes()
    for attempt in range(4):  # a box of grid points around the star, moved while the fit stops at its edge
        progress(0.5 + 0.1 * attempt, "fit")
        out = atm.analyse(w, f, e, grid_of(atm.neighbourhood(*centre), 0.5), R, ref, air=air)
        raw = tuple(out["raw"][k] for k in names)
        # an edge of this box that is not the edge of the whole PHOENIX grid: move the box there
        inner = [k for k, v, ax in zip(names, raw, axes, strict=True) if k in out["at_edge"] and ax[0] < v < ax[-1]]
        if not inner:
            break
        centre = raw
    return {"atmosphere": _atmosphere_out(out)}


def _atmosphere_out(out):
    keep = ("teff", "logg", "feh", "vsini", "rv", "errors", "raw", "sun_offsets", "sun_fit", "chi2_red", "n")
    return {k: out[k] for k in keep} | {
        "used_fraction": out["used_fraction"],
        "far_from_sun": out["far_from_sun"],
        "at_edge": out["at_edge"],
        "plot": {"wave": out["wave"], "flux": out["flux"], "model": out["model"]},
    }


@step("spectroscopy.orders", inputs=("image",), outputs=("orders",), orientation="x", reverse=False, rows=None)
def orders_step(inputs, params, ctx):
    """Orders of an echelle flat (or bright star) found and traced, to be checked on the Echelle tab: rows at the
    central column, trace coefficients, and the rows that could not be traced. rows: start from these instead of
    the automatic search (after the user removed or added orders)."""
    flat = _load(inputs["image"], params)[0]
    rows = echelle.find_orders(flat) if params["rows"] is None else params["rows"]
    kept, coefs, failed = echelle.trace_each(flat, rows)
    return {"orders": {"rows": kept, "traces": [c.tolist() for c in coefs], "failed": failed, "nx": flat.shape[1]}}


def _write_orders(output, waves, flux, err, orders, header):
    """Every order on its own: <output>_orders.fits with FLUX, ERROR and WAVE images (one row per order)."""
    from astropy.io import fits

    path = Path(output)
    path = path.with_name(path.stem + "_orders.fits")
    h = header.copy()
    h["ORDERS"] = (",".join(str(o) for o in orders), "absolute order number of each row")
    hdus = [fits.PrimaryHDU(np.asarray(flux, np.float32), h)]
    hdus += [fits.ImageHDU(np.asarray(err, np.float32), name="ERROR"), fits.ImageHDU(np.asarray(waves), name="WAVE")]
    fits.HDUList(hdus).writeto(path, overwrite=True, output_verify="silentfix")
    return str(path)


@step("spectroscopy.telluric", inputs=("spectrum", "standard"), outputs=("telluric",), optional=("output",))
def telluric_step(inputs, params, ctx):
    """Divide out the atmosphere measured in a telluric standard (strength and shift fitted)."""
    w, f, e, header = spectrum_io.read(inputs["spectrum"])
    sw, sf, _, _ = spectrum_io.read(inputs["standard"])
    r = telluric.correct(w, f, sw, sf)
    err = None if e is None else e / r["transmission"]
    out = {
        "wave": w.tolist(),
        "flux": f.tolist(),
        "corrected": np.where(
            r["bad"], np.nan, r["flux"]
        ).tolist(),  # saturated cores: no information (they spiked to ±10)
        "transmission": r["transmission"].tolist(),
        "power": r["power"],
        "shift_kms": r["shift_kms"],
    }
    if inputs.get("output"):
        header["TELLPOW"] = (r["power"], "telluric optical depth scale vs standard")
        header["TELLSHFT"] = (r["shift_kms"], "telluric standard shift (km/s)")
        flux = np.where(r["bad"], np.nan, r["flux"])  # saturated bands: no information left
        out["path"] = spectrum_io.write(
            inputs["output"], w, flux, err if err is not None else np.full(len(w), np.nan), header
        )
    return {"telluric": out}


@step(
    "spectroscopy.combine",
    inputs=("spectra",),
    outputs=("combined",),
    optional=("output",),
    method="mean",
    rejection="sigma",
    sigma=3.0,
    scale="median",
    weight="none",
)
def combine_step(inputs, params, ctx):
    """Several exposures of one star in a night combined into one spectrum (IRAF scombine), see combine.py."""
    from . import combine

    spectra, header, mjd = [], None, []
    for path in inputs["spectra"]:
        w, f, e, h = spectrum_io.read(path)
        spectra.append((w, f, e))
        header = header if header is not None else h
        if number(h.get("MJD-OBS")) is not None:
            mjd.append(number(h.get("MJD-OBS")))
    r = combine.combine(spectra, params["method"], params["rejection"], params["sigma"], params["scale"],
                        params["weight"])  # fmt: skip
    out = {k: np.asarray(v).tolist() for k, v in r.items() if k in ("wave", "flux", "error", "n", "scales")}
    out |= {"rejected": r["rejected"], "count": len(spectra), "warnings": []}
    if len(mjd) > 1 and max(mjd) - min(mjd) > 0.5:  # archive file names are processing dates, not nights
        out["warnings"].append(
            f"the exposures span {max(mjd) - min(mjd):.1f} days: the star's velocity changes between nights; "
            "combine one night at a time, or shift the spectra to one velocity first"
        )
    if inputs.get("output"):
        header["NCOMBINE"] = (len(spectra), "exposures combined")
        header["COMBMETH"] = (f"{params['method']}/{params['rejection']}", "combine / rejection")
        out["path"] = spectrum_io.write(inputs["output"], r["wave"], r["flux"], r["error"], header)
    return {"combined": out}


@step(
    "spectroscopy.rv",
    inputs=("spectra", "template"),
    outputs=("rvs", "skipped"),
    optional=("coord", "site", "template2"),
    v_min=-300.0,
    v_max=300.0,
    wave_min=None,
    wave_max=None,
    method="ccf",
    components=1,
    template_rv=0.0,
    template2_rv=None,
    template_vsini=0.0,
    template2_vsini=0.0,
)
def rv_step(inputs, params, ctx):
    """Radial velocity of each spectrum against a template, barycentric-corrected when the header
    gives the time and the sky position (or coord) and a site is known. With a second template
    (double-lined binary) both components are measured with TODCOR. method="bf": the broadening
    function with `components` rotational profiles (fast rotators, contact binaries); also v sin i.
    template_rv / template2_rv: the templates' own velocities (km/s; a real star's spectrum is not at rest: tau
    Ceti -16.5, put on every velocity of TZ For); the second defaults to the first. template_vsini / template2_vsini:
    the templates' lines broadened by rotation (km/s) to match each star (a fast rotator against a sharp template)."""
    v_t1 = float(params["template_rv"] or 0.0)
    v_t2 = v_t1 if params["template2_rv"] is None else float(params["template2_rv"])
    from ..photometry.lightcurve import target_coord
    from ..planning.visibility import Site

    tw0, tf0, _, _ = spectrum_io.read(inputs["template"])
    good = np.isfinite(tf0)  # a template's gap (NaN) is bridged by interpolation: no lines, not zero flux
    tw0, tf0 = rv.rotate(tw0[good], rv.continuum_normalise(tw0[good], tf0[good]), params["template_vsini"])
    t2 = None
    if inputs.get("template2"):
        t2w, t2f, _, _ = spectrum_io.read(inputs["template2"])
        good = np.isfinite(t2f)
        t2 = rv.rotate(t2w[good], rv.continuum_normalise(t2w[good], t2f[good]), params["template2_vsini"])
    site = Site(**inputs["site"]).location if inputs.get("site") else None
    rows, skipped = [], []
    for i, path in enumerate(inputs["spectra"]):
        ctx.check()
        ctx.progress(i / len(inputs["spectra"]), Path(path).name)
        w, f, _, h = spectrum_io.read(path)
        sel = np.isfinite(f) & (w >= (params["wave_min"] or -np.inf)) & (w <= (params["wave_max"] or np.inf))
        if sel.sum() < 50:  # an ARAS spectrum of 6578-8634 A among 5000-5800 A ones stopped the whole batch
            skipped.append({"file": Path(path).name, "from": float(np.nanmin(w)), "to": float(np.nanmax(w))})
            continue
        w, f = w[sel], rv.continuum_normalise(w[sel], f[sel])
        tw, tf = rv.match_template(w, tw0, tf0)  # a much finer template is brought to this spectrum's resolution
        matched = tw is not tw0
        air = "converted to air" in str(h.comments["VACUUM"] if "VACUUM" in h else "")
        if params["method"] == "bf":
            b = bf.broadening_function(w, f, tw, tf, params["v_min"], params["v_max"], components=params["components"])
            c = b["components"]
            r = {"rv": c[0]["rv"], "rv_err": c[0]["rv_err"], "peak": None}
            profile = {"kind": "bf", "v": b["v"], "y": b["bf_smooth"], "model": b["model"]}
            r2 = {"vsini": c[0]["vsini"], "vsini_err": c[0]["vsini_err"]}
            if len(c) > 1:
                ratio = c[1]["strength"] / c[0]["strength"]
                r2 |= {"rv2_obs": c[1]["rv"], "rv2_err": c[1]["rv_err"], "flux_ratio": ratio, "rv2": None}
                r2 |= {"vsini2": c[1]["vsini"], "vsini2_err": c[1]["vsini_err"]}
        elif t2 is None:
            f, masked = rv.mask_emission(f, tf)
            r = rv.ccf(w, f, tw, tf, params["v_min"], params["v_max"])
            profile = {"kind": "ccf", "v": r["v"], "y": r["ccf"]}
            r["emission_masked"] = masked
            r["rv_err_formal"] = r["rv_err"]
            empirical = rv.chunk_error(w, f, tw, tf, params["v_min"], params["v_max"])
            if empirical is not None and empirical > r["rv_err"]:  # the parts disagree more than the formula says
                r["rv_err"] = empirical
            r2 = {}
        else:
            d = sb2.todcor(w, f, tw, tf, *rv.match_template(w, *t2), params["v_min"], params["v_max"])
            r = {"rv": d["rv1"], "rv_err": d["rv1_err"], "peak": d["peak"]}
            r2 = {"rv2_obs": d["rv2"], "rv2_err": d["rv2_err"], "flux_ratio": d["flux_ratio"], "rv2": None}
            profile = {"kind": "todcor", "v": d["v"], "y": d["profile1"], "y2": d["profile2"]}
        r["rv"] += v_t1  # against the template's rest frame -> the star's velocity
        if r2.get("rv2_obs") is not None:
            r2["rv2_obs"] += v_t2 if t2 is not None else v_t1  # the broadening function's 2nd star: same template
        row = {
            "file": Path(path).name,
            "rv_obs": r["rv"],
            "rv_err": r["rv_err"],
            "rv_err_formal": r.get("rv_err_formal", r["rv_err"]),  # the CCF formula; rv_err may be the empirical one
            "ccf_peak": r["peak"],
            # what the velocity was read from (fxcor shows it): CCF, broadening function or TODCOR, in the
            # template's frame (add the template's own velocity to read it as the star's)
            "profile": _thin(profile),
            "time_jd": None,
            "bjd": None,
            "v_corr": None,
            "rv": None,
            "site": None,  # where the barycentric correction was computed for, shown to the user
            "template_matched": matched,  # shown to the user: choices made for them stay visible
            "emission_masked": r.get("emission_masked", 0),
            "vacuum_to_air": air,
        } | r2
        # archive spectra (ESO Phase 3, LAMOST's HELIO, BeSS / ARAS BSS_VHEL, many pipelines) may already be on the
        # barycentric (or heliocentric, within 12 m/s) scale: correcting them again put a constant star 27 km/s off
        already = (
            str(h.get("SPECSYS", "")).strip().upper().startswith(("BARYCENT", "HELIOCEN"))
            or h.get("HELIO") is True
            or bool(number(h.get("BSS_VHEL")))  # BeSS: the heliocentric correction applied (0 = none)
        )
        if already:
            row |= {"v_corr": 0.0, "rv": r["rv"], "already_barycentric": True}
            if "rv2_obs" in r2:  # a second star (r2 alone may hold one star's v sin i)
                row["rv2"] = r2["rv2_obs"]
        try:
            t = timing.mid_time(h)
            sky = target_coord(h, inputs.get("coord"))
            row["time_jd"] = t.utc.jd
            where = site if site is not None else timing.location(h)  # the Plan page's site, else the header
            if sky is not None:
                row["bjd"] = timing.bjd_tdb(t, sky, where).jd
                if where is not None and not already:
                    row["v_corr"] = rv.barycentric_correction(t, sky, where)
                    geo = where.to_geodetic()
                    row["site"] = {
                        "lat": float(geo.lat.deg),
                        "lon": float(geo.lon.deg),
                        "from": "plan" if site is not None else "header",
                    }
                    row["rv"] = rv.to_barycentric(r["rv"], row["v_corr"])
                    if "rv2_obs" in r2:
                        row["rv2"] = rv.to_barycentric(r2["rv2_obs"], row["v_corr"])
        except (timing.TimeError, ValueError):
            pass  # no usable time: the velocity is still reported, without correction
        rows.append(row)
    if not rows:
        raise ValueError("no spectrum covers the chosen wavelengths: widen the range or set it to 0 (all)")
    return {"rvs": rows, "skipped": skipped}


@step(
    "spectroscopy.orbit",
    inputs=("time", "rv"),
    outputs=("orbit",),
    optional=("error", "rv2", "error2"),
    period=None,
    fix_period=False,
)
def orbit_step(inputs, params, ctx):
    """Keplerian orbit; double-lined (shared elements, K1 and K2) when rv2 is given."""
    if not params["period"]:
        raise ValueError("give a period guess (e.g. from the period search)")
    if inputs.get("rv2") is not None:
        t = inputs["time"]
        fit = orbit.fit_sb2(
            t,
            inputs["rv"],
            t,
            inputs["rv2"],
            inputs.get("error"),
            inputs.get("error2"),
            period=params["period"],
            fix_period=params["fix_period"],
        )
        return {"orbit": fit}
    fit = orbit.fit_orbit(
        inputs["time"], inputs["rv"], inputs.get("error"), period=params["period"], fix_period=params["fix_period"]
    )
    return {"orbit": fit}


def spectrum_name(science_path):
    return re.sub(r"\.(fits?|fts)(\.gz|\.fz)?$", "", Path(science_path).name, flags=re.I) + "_1d.fits"


@step("spectroscopy.classify", inputs=("spectrum", "library"), outputs=("classes",), fwhm=None)
def classify_step(inputs, params, ctx):
    """Spectral type from the best-matching library templates; the Pickles library is fetched if the folder
    is empty (needs the internet once)."""
    from . import templates

    w, f, _, _ = spectrum_io.read(inputs["spectrum"])  # a wrong file fails now, not after a long download
    folder = Path(inputs["library"])
    paths = sorted(folder.glob("*.fits")) + sorted(folder.glob("*.fit"))
    out = {"classes": [], "mk": None, "mk_note": None, "mk_model": None, "classes_note": None}
    try:
        if not paths:
            ctx.progress(0.05, "downloading the template library")
            paths = templates.download_pickles(folder)
        ctx.progress(0.5, "comparing")
        ranked = templates.classify(w, f, paths, params["fwhm"])
        out["classes"] = [{"type": t, "rms": r, "template": p} for t, r, p in ranked]
    except OSError as e:  # the library could not be fetched: the MK type below does not need it
        out["classes_note"] = str(e)
    # the MK type against the MK standards themselves (Gray & Corbally), as a ranked suggestion
    from . import mkstandards

    try:
        ctx.progress(0.7, "comparing with the MK standards")
        folder = mkstandards.download(Path(inputs["library"]) / "mk_libnor36")
        out["mk"], out["mk_model"] = mkstandards.classify(w, f, folder, params["fwhm"])
    except (OSError, ValueError) as e:  # offline, or the spectrum misses 3800-5600 A: the library ranking stays
        out["mk_note"] = str(e)
    return out


@step(
    "spectroscopy.disentangle",
    inputs=("spectra", "rv1", "rv2", "output_dir"),
    outputs=("components",),
    optional=("light_ratio",),
    iterations=40,
)
def disentangle_step(inputs, params, ctx):
    """The two stars' spectra of a double-lined binary from the series and its observed velocities."""
    from .disentangle import disentangle, separable_width

    waves, fluxes = [], []
    for i, p in enumerate(inputs["spectra"]):
        ctx.progress(0.5 * i / len(inputs["spectra"]), "reading")
        w, f, _, _ = spectrum_io.read(p)
        ok = np.isfinite(f)
        waves.append(w[ok])
        fluxes.append(rv.continuum_normalise(w[ok], f[ok]))
    ctx.progress(0.6, "disentangling")
    wave, s1, s2 = disentangle(
        waves,
        fluxes,
        np.asarray(inputs["rv1"], float),
        np.asarray(inputs["rv2"], float),
        inputs.get("light_ratio"),
        params["iterations"],
    )
    out = Path(inputs["output_dir"])
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, s in (("star1", s1), ("star2", s2)):
        paths.append(str(spectrum_io.write(out / f"{name}.fits", wave, s, np.full(len(wave), np.nan))))
    width = separable_width(inputs["rv1"], inputs["rv2"])
    return {
        "components": {"paths": paths, "wave": wave.tolist(), "star1": s1.tolist(), "star2": s2.tolist(),
                       "separable_kms": width, "separable_a": width / rv.C_KMS * float(np.median(wave))}
    }  # fmt: skip
