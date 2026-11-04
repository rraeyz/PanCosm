"""Spectroscopy as engine steps."""

import re
from pathlib import Path

import numpy as np

from .. import timing
from ..calibration.masters import load
from ..engine.steps import step
from ..hdr import get
from . import bf, echelle, longslit, orbit, rv, sb2, spectrum_io, telluric, wavecal


def _oriented(data, params):
    """Dispersion along x, wavelength increasing to the right (coude and other spectrographs often
    disperse along the columns, or towards smaller pixel numbers)."""
    if params.get("orientation", "x") == "y":
        data = data.T
    return data[:, ::-1] if params.get("reverse") else data


def _load(path, params):
    data, header = load(path)
    return _oriented(data, params), header


@step(
    "spectroscopy.reduce",
    inputs=("science",),
    outputs=("spectrum",),
    optional=("arc", "guesses", "output"),
    guess_row=None,
    width=10.0,
    sky_offset=15.0,
    sky_width=10.0,
    optimal=True,
    gain=None,
    read_noise=5.0,
    line_list="henear",
    order=3,
    orientation="x",
    reverse=False,
)
def reduce_step(inputs, params, ctx):
    """2-D long-slit/slitless frame (dispersion along x) -> 1-D spectrum; wavelengths from an arc
    when an arc and at least two identified (pixel, wavelength) pairs are given."""
    data, header = _load(inputs["science"], params)
    ctx.progress(0.1, "trace")
    coef = longslit.trace(data, params["guess_row"])
    gain = float(params["gain"] or get(header, "EGAIN", "GAIN", default=1.0) or 1.0)
    w, so, sw = params["width"], params["sky_offset"], params["sky_width"]
    ctx.progress(0.4, "extraction")
    if params["optimal"]:
        flux, err, sky, _ = longslit.optimal(data, coef, w, so, sw, gain, params["read_noise"])
    else:
        flux, sky = longslit.boxcar(data, coef, w, so, sw)
        err = np.sqrt(np.clip(flux, 0, None) / gain + w * (params["read_noise"] / gain) ** 2)
    out = {
        "pixel": np.arange(len(flux)).tolist(),
        "flux": flux.tolist(),
        "error": err.tolist(),
        "trace": coef.tolist(),
        "wave": None,
        "arc_peaks": [],
        "solution": None,
    }
    if inputs.get("arc"):
        ctx.progress(0.7, "arc")
        arc, _ = _load(inputs["arc"], params)
        arc1d, _ = longslit.boxcar(arc, coef, w, subtract_sky=False)
        peaks = wavecal.find_lines(arc1d)
        out["arc"] = arc1d.tolist()
        out["arc_peaks"] = peaks.tolist()
        if inputs.get("guesses") and len(inputs["guesses"]) >= 2:
            # the user's identified wavelengths are lines of the lamp too (e.g. Hg in an HgAr lamp, not in the list)
            catalogue = np.union1d(wavecal.load_line_list(params["line_list"]), [g[1] for g in inputs["guesses"]])
            sol = wavecal.solve(peaks, catalogue, inputs["guesses"], params["order"])
            out["wave"] = sol(np.arange(len(flux))).tolist()
            out["solution"] = {"coef": sol.coef.tolist(), "rms": sol.rms, "n_lines": sol.n_lines}
    if inputs.get("output") and out["wave"] is not None:
        header["WAVSOLRM"] = (out["solution"]["rms"], "wavelength solution rms (Angstrom)")
        header["WAVSOLN"] = (out["solution"]["n_lines"], "arc lines used")
        out["path"] = spectrum_io.write(inputs["output"], out["wave"], flux, err, header)
    return {"spectrum": out}


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
    deg_x=4,
    deg_m=3,
    min_blaze=0.1,
    orientation="x",
    reverse=False,
    sky=True,
    scatter=False,
    exclude=[],
    rows=None,
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
    are also written one by one (<output>_orders.fits: flux, error and wavelength images, one row per order)."""
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
    flux, err = echelle.extract(
        data, coefs, method=method, subtract_sky=params["sky"], gain=gain, read_noise=params["read_noise"]
    )
    bl = echelle.blaze(echelle.extract(flat, coefs, method="boxcar")[0]) if flat is not None else None
    nx = data.shape[1]
    first = params["first_order"]
    orders = None if first is None else [int(first) + params["order_step"] * k for k in range(len(coefs))]
    out = {
        "n_orders": len(coefs),
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
    if inputs.get("arc"):
        ctx.progress(0.6, "arc")
        arc = echelle.extract(_load(inputs["arc"], params)[0], coefs, method="boxcar", subtract_sky=False)[0]
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
            w, f, e = echelle.merge(waves, flux, err, bl, params["min_blaze"])
            out["wave"] = waves.tolist()
            out["solution"] = {"rms": sol.rms, "n_lines": sol.n_lines, "lines": sol.lines}
            out["merged"] = {"wave": w.tolist(), "flux": f.tolist(), "error": e.tolist()}
            if inputs.get("output"):
                header["WAVSOLRM"] = (sol.rms, "echelle wavelength solution rms (Angstrom)")
                header["WAVSOLN"] = (sol.n_lines, "arc lines used")
                header["NORDERS"] = (len(coefs), "orders merged")
                out["path"] = spectrum_io.write(inputs["output"], w, f, e, header)
                out["orders_path"] = _write_orders(inputs["output"], waves, flux, err, orders, header)
    return {"echelle": out}


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
        "corrected": r["flux"].tolist(),
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
    "spectroscopy.rv",
    inputs=("spectra", "template"),
    outputs=("rvs",),
    optional=("coord", "site", "template2"),
    v_min=-300.0,
    v_max=300.0,
    wave_min=None,
    wave_max=None,
    method="ccf",
    components=1,
)
def rv_step(inputs, params, ctx):
    """Radial velocity of each spectrum against a template, barycentric-corrected when the header
    gives the time and the sky position (or coord) and a site is known. With a second template
    (double-lined binary) both components are measured with TODCOR. method="bf": the broadening
    function with `components` rotational profiles (fast rotators, contact binaries); also v sin i."""
    from ..photometry.lightcurve import target_coord
    from ..planning.visibility import Site

    tw, tf, _, _ = spectrum_io.read(inputs["template"])
    tf = rv.continuum_normalise(tw, tf)
    t2 = None
    if inputs.get("template2"):
        t2w, t2f, _, _ = spectrum_io.read(inputs["template2"])
        t2 = (t2w, rv.continuum_normalise(t2w, t2f))
    site = Site(**inputs["site"]).location if inputs.get("site") else None
    rows = []
    for i, path in enumerate(inputs["spectra"]):
        ctx.check()
        ctx.progress(i / len(inputs["spectra"]), Path(path).name)
        w, f, _, h = spectrum_io.read(path)
        sel = np.isfinite(f) & (w >= (params["wave_min"] or -np.inf)) & (w <= (params["wave_max"] or np.inf))
        w, f = w[sel], rv.continuum_normalise(w[sel], f[sel])
        if params["method"] == "bf":
            b = bf.broadening_function(w, f, tw, tf, params["v_min"], params["v_max"], components=params["components"])
            c = b["components"]
            r = {"rv": c[0]["rv"], "rv_err": c[0]["rv_err"], "peak": None}
            r2 = {"vsini": c[0]["vsini"], "vsini_err": c[0]["vsini_err"]}
            if len(c) > 1:
                ratio = c[1]["strength"] / c[0]["strength"]
                r2 |= {"rv2_obs": c[1]["rv"], "rv2_err": c[1]["rv_err"], "flux_ratio": ratio, "rv2": None}
                r2 |= {"vsini2": c[1]["vsini"], "vsini2_err": c[1]["vsini_err"]}
        elif t2 is None:
            r = rv.ccf(w, f, tw, tf, params["v_min"], params["v_max"])
            r2 = {}
        else:
            d = sb2.todcor(w, f, tw, tf, *t2, params["v_min"], params["v_max"])
            r = {"rv": d["rv1"], "rv_err": d["rv1_err"], "peak": d["peak"]}
            r2 = {"rv2_obs": d["rv2"], "rv2_err": d["rv2_err"], "flux_ratio": d["flux_ratio"], "rv2": None}
        row = {
            "file": Path(path).name,
            "rv_obs": r["rv"],
            "rv_err": r["rv_err"],
            "ccf_peak": r["peak"],
            "time_jd": None,
            "bjd": None,
            "v_corr": None,
            "rv": None,
            "site": None,  # where the barycentric correction was computed for, shown to the user
        } | r2
        try:
            t = timing.mid_time(h)
            sky = target_coord(h, inputs.get("coord"))
            row["time_jd"] = t.utc.jd
            where = site if site is not None else timing.location(h)  # the Plan page's site, else the header
            if sky is not None:
                row["bjd"] = timing.bjd_tdb(t, sky, where).jd
                if where is not None:
                    row["v_corr"] = rv.barycentric_correction(t, sky, where)
                    geo = where.to_geodetic()
                    row["site"] = {
                        "lat": float(geo.lat.deg),
                        "lon": float(geo.lon.deg),
                        "from": "plan" if site is not None else "header",
                    }
                    row["rv"] = rv.to_barycentric(r["rv"], row["v_corr"])
                    if r2:
                        row["rv2"] = rv.to_barycentric(r2["rv2_obs"], row["v_corr"])
        except (timing.TimeError, ValueError):
            pass  # no usable time: the velocity is still reported, without correction
        rows.append(row)
    return {"rvs": rows}


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
    if not paths:
        ctx.progress(0.05, "downloading the template library")
        paths = templates.download_pickles(folder)
    ctx.progress(0.5, "comparing")
    ranked = templates.classify(w, f, paths, params["fwhm"])
    return {"classes": [{"type": t, "rms": r, "template": p} for t, r, p in ranked]}


@step(
    "spectroscopy.disentangle",
    inputs=("spectra", "rv1", "rv2", "output_dir"),
    outputs=("components",),
    optional=("light_ratio",),
    iterations=40,
)
def disentangle_step(inputs, params, ctx):
    """The two stars' spectra of a double-lined binary from the series and its observed velocities."""
    from .disentangle import disentangle

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
    return {"components": {"paths": paths, "wave": wave.tolist(), "star1": s1.tolist(), "star2": s2.tolist()}}
