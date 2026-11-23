"""Calibration as engine steps (run in worker processes, recorded in the project)."""

import re
from pathlib import Path

from ..core import provenance
from ..core.atomic import write_fits
from ..core.errors import AppError
from ..engine.steps import step
from ..hdr import get
from ..io import bayer
from ..io.lzw import readable
from . import library_use, master_method, masters, planes_out, trails_run
from .frames import Frame, scan
from .matching import apply_choices, best_bias, best_dark, group_key, make_plan


@step(
    "calibration.scan",
    inputs=("folder",),
    outputs=("frames", "problems", "raw_converted"),
    optional=("lights",),
    clock_utc_offset=0.0,
    rules=(),
    filter_aliases={},
)
def scan_step(inputs, params, ctx):
    """Camera raw files (DSLR, mirrorless) in the folder are first written as FITS to folder/fits_from_raw.
    folder: calibration frames (bias / dark / flat) or everything mixed, several separated by ";"; lights: a folder
    of light frames — as observers keep them (a BDF folder and a data folder), every frame there is a light whatever
    its name, unless its own header states another type."""
    from ..io.bayer import convert_raw_folder
    from .frames import classify

    folders = [f.strip() for f in str(inputs.get("folder") or "").split(";") if f.strip()]
    light_dirs = [f.strip() for f in str(inputs.get("lights") or "").split(";") if f.strip()]
    if not folders and not light_dirs:
        # nothing given: said like a wrong one
        raise AppError("folder not found: {path}", path=inputs.get("folder") or "")
    for folder in folders + light_dirs:
        if not Path(folder).is_dir():
            raise AppError("folder not found: {path}", path=folder)
    frames, problems, raw = {}, [], []
    every = [(f, "calibration") for f in folders] + [(f, "lights") for f in light_dirs]
    for i, (folder, role) in enumerate(every):
        part = (i, len(every))
        converted, raw_problems = convert_raw_folder(
            folder,
            clock_utc_offset_h=params["clock_utc_offset"],
            progress=lambda f, n, p=part: ctx.progress(0.5 * (p[0] + f) / p[1], n),
        )
        raw += converted
        ctx.progress(0.5 + 0.5 * i / len(every), "reading headers")
        found, bad = scan(Path(folder))
        if role == "lights":  # the folder says what they are; only a header stating a calibration type overrides
            for f in found:
                stated = classify(_frame_header(f.path))
                f.kind = stated if stated in ("bias", "dark", "flat", "arc") else "light"
        frames |= {str(Path(f.path).resolve()): f for f in found}  # a folder inside another one is read once
        problems += raw_problems + bad
    _apply_rules(frames.values(), params.get("rules") or (), params.get("filter_aliases") or {})
    return {
        "frames": [frames[p].as_dict() for p in sorted(frames)],
        "problems": problems,
        "raw_converted": len(raw),
    }


def _apply_rules(frames, rules, aliases):
    """CAL-2 item 3: the user's own rules ("OBSTYPE = SKY is a flat") over the built-in conventions, and filter names
    that mean the same filter ("Clear", "L", "Lum")."""
    from .frames import rule_kind

    lower = {str(k).strip().lower(): v for k, v in aliases.items()}
    for f in frames:
        if rules:
            kind = rule_kind(_frame_header(f.path), rules)
            f.kind = kind or f.kind
        if f.filter is not None and f.filter.strip().lower() in lower:
            f.filter = lower[f.filter.strip().lower()]


def _frame_header(path):
    """The header that describes the image of a frame (the primary's keywords included, as read_frame reads it)."""
    from astropy.io import fits

    from ..io.fits import find_image_hdu, inherited

    with fits.open(readable(path)) as hdul:
        return inherited(hdul, find_image_hdu(hdul))


def _frames(dicts):
    return [Frame(**d | {"binning": tuple(d["binning"]), "shape": tuple(d["shape"])}) for d in dicts]


def _unused_groups(plan, reps, temp_tol):
    """Groups of bias / darks / flats that no light needs, directly or through the flats and darks it uses: not
    combined (on a real LCO night, full-chip bias and darks of 61 MP next to the lights' 2400 x 2400 crop took most of
    the time). Without lights every group is a wanted master."""
    if not plan.lights:
        return []
    need = {e[k] for e in plan.lights for k in ("bias", "dark", "flat") if e.get(k)}
    biases = [reps[k] for k in plan.groups if k[0] == "bias"]
    darks = [reps[k] for k in plan.groups if k[0] == "dark"]
    for key in [k for k in need if k[0] in ("dark", "flat")]:  # what a dark or flat master is made with
        b = best_bias(reps[key], biases)
        need |= {group_key(b)} if b else set()
        if key[0] == "flat":
            d = best_dark(reps[key], darks, temp_tol, lambda _: bool(biases))
            need |= {group_key(d)} if d else set()
            if d and (b2 := best_bias(d, biases)):
                need.add(group_key(b2))
    return [k for k in plan.groups if k not in need]


@step(
    "calibration.run",
    inputs=("frames", "output_dir"),
    outputs=("masters", "calibrated", "missing", "failed_masters", "arcs", "dark_scales", "trails", "master_methods"),
    sigma=3.0,
    master_combine=master_method.DEFAULT,
    camera_read_noise=0.0,
    temp_tol=2.0,
    cosmic_rays=False,
    read_noise=10.0,
    optimize_dark=False,
    fix_defects=False,
    divide_flat=True,
    split_colour=True,
    linearity=(),
    use={},
    write_planes=True,
    find_trails=False,
    gain=0.0,
    saturation=0.0,
    library_folder="",
)
def run_step(inputs, params, ctx):
    """Build every master the plan needs, then calibrate every light. Missing corrections are skipped and listed.
    linearity: coefficients c0, c1, c2... of the camera's linearity correction (masters.linearity), or empty."""
    from .output import check_space, estimate

    need = estimate(inputs["frames"], params.get("split_colour", False), params.get("write_planes", True))
    check_space(inputs["output_dir"], need)  # CAL-14: refused before anything is written, with the numbers
    with masters.linearity(params["linearity"]):
        out = _run(inputs, params, ctx)
    out["estimated_bytes"] = need
    out["scaled_glow"] = _scaled_glow(out, inputs["frames"])
    return out


def _scaled_glow(out, frames):
    """CAL-3: master darks with amplifier glow whose exposure differs from the lights' — scaling them leaves the glow
    wrong (it does not grow in proportion to time). [{dark, dark_exptime, light_exptimes}]."""
    from astropy.io import fits

    light_times = sorted(
        {round(float(f["exptime"]), 3) for f in frames if f.get("kind") == "light" and f.get("exptime")}
    )
    warn = []
    for path in out.get("masters") or []:
        name = Path(path).name
        if (out.get("quality", {}).get(name, {}).get("amp_glow") or {}).get("ok", True):
            continue
        t = float(fits.getheader(path).get("EXPTIME", 0.0) or 0.0)
        others = [x for x in light_times if abs(x - t) > 0.1 * max(x, t)]
        if others:
            warn.append({"dark": name, "dark_exptime": t, "light_exptimes": others})
    return warn


def _chosen(plan, frames, use):
    """The masters chosen by hand over the program's matches (matching.apply_choices); a name of no group refused."""
    wrong = apply_choices(plan, frames, use)
    if wrong:
        kind, pick = wrong[0][1], Path(wrong[0][2]).name
        raise AppError("{pick} is not a {kind} frame of this night: choose another", pick=pick, kind=kind)
    return plan


def _order(plan, reps, kinds, temp_tol):
    """(groups no light needs, the groups to combine: bias, then darks, then flats — flats need bias + dark)."""
    unused = _unused_groups(plan, reps, temp_tol)  # e.g. full-chip bias next to the cropped lights' (real LCO night)
    wanted = (k for k in plan.groups if k not in unused)
    return unused, sorted(wanted, key=lambda k: ("bias", "dark", "flat").index(kinds[k]))


def _record_masters(header, entry, built, flat_used, params):
    """CALB / CALD / CALF keywords and the provenance record of one calibrated light (ARC-11)."""
    used = {k: built[entry[k]][2] for k in ("bias", "dark", "flat") if entry[k] and (k != "flat" or flat_used)}
    for kind in ("bias", "dark", "flat"):
        header[f"CAL{kind[0].upper()}"] = (Path(used.get(kind, "none")).name, f"{kind} used for calibration")
    provenance.to_fits(header, provenance.record("calibration.run", params, {"light": entry["light"], **used}))


def _master(kind, paths, bias, dark, params, var):
    """One master of `kind` made the way the run's master_combine says; dark: (data, header) for a flat."""
    how, sigma = master_method.pick(kind, paths, params), params["sigma"]
    if kind == "bias":
        return masters.master_bias(paths, sigma, var_out=var, how=how)
    if kind == "dark":
        return masters.master_dark(paths, bias, sigma, var_out=var, how=how)
    return masters.master_flat(paths, bias, *dark, sigma, var_out=var, how=how)


def _run(inputs, params, ctx):
    frames = _frames(inputs["frames"])
    plan = _chosen(make_plan(frames, params["temp_tol"]), frames, params.get("use") or {})
    out = Path(inputs["output_dir"])
    (out / "masters").mkdir(parents=True, exist_ok=True)
    built = {}  # group key -> (data, header, path)
    kinds = {key: key[0] for key in plan.groups}
    reps = {group_key(f): f for f in frames if f.kind in kinds.values()}  # one representative frame per group

    def best(kind, rep):  # the already built master of `kind` that matches frame `rep`, by the plan's rules
        cands = [reps[k] for k in built if k[0] == kind]
        m = best_bias(rep, cands) if kind == "bias" else best_dark(rep, cands, temp_tol, lambda _: has_bias())
        return built[group_key(m)] if m else (None, None, None)

    def has_bias():
        return any(k[0] == "bias" for k in built)

    temp_tol = params["temp_tol"]
    unused, order = _order(plan, reps, kinds, temp_tol)
    from_library = library_use.fill(plan, frames, params.get("library_folder"))  # what the night lacks (CAL-7)
    failed, qc = [], {}  # masters not made (their frames left out, lights calibrated without); the reports (CAL-6)
    variances = {}  # group key -> the master's variance plane (CAL-13)
    methods = {}  # master file name -> how it was combined
    for n, key in enumerate(order):
        ctx.check()
        ctx.progress(0.5 * n / max(1, len(order)), f"master {kinds[key]}")
        paths, rep = plan.groups[key], reps[key]
        bias, v = best("bias", rep)[0], {}  # v: the master's variance, σ² / N (CAL-13)
        try:
            # no matching dark is fine for flats: they are bright, dark current is < 0.1 % of them
            dark = best("dark", rep) if kinds[key] == "flat" else (None, None, None)
            data, h = _master(kinds[key], paths, bias, dark[:2], params, v)
        except masters.CalibrationError as e:  # one bad group (e.g. flats that are not flats) must not stop the night
            failed.append({"kind": kinds[key], "frames": len(paths), "file": Path(paths[0]).name, "reason": str(e)})
            continue
        var = v.get("var")
        if var is not None:
            var = var.astype("float32").astype("float64")  # as a master file keeps it: a live run reads the same
        keep = var if params.get("write_planes", True) else None
        built[key] = (data, h, _save_master(out, kinds[key], n, data, h, qc, paths, bias, keep))
        methods[Path(built[key][2]).name] = h["COMBINE"]
        variances[key] = var

    built |= from_library
    calibrated, arcs, defect_maps, dark_scales, found_trails = [], [], {}, [], []
    lamps = {f.path for f in frames if f.kind == "arc"}  # calibrated, but kept out of the stacks and photometry
    lights = plan.lights
    for n, entry in enumerate(lights):
        ctx.check()
        ctx.progress(0.5 + 0.5 * n / max(1, len(lights)), "calibrating")
        light, header = masters.load(entry["light"])
        entry = {k: (v if k == "light" or v in built else None) for k, v in entry.items()}  # failed masters
        b = built[entry["bias"]][0] if entry["bias"] else None
        d, dh = (built[entry["dark"]][0], built[entry["dark"]][1]) if entry["dark"] else (None, None)
        # spectra: an echelle / long-slit flat is not a sensitivity map (its gaps between orders are near zero);
        # it is built as a master and used by the spectroscopy page for tracing and the blaze instead
        f = built[entry["flat"]][0] if entry["flat"] and params["divide_flat"] else None
        exptime = get(header, "EXPTIME", "EXPOSURE", default=0.0)
        k, defects = 1.0, None
        if params["optimize_dark"] and d is not None:
            signal = masters.dark_for(exptime, b, d, dh)
            k = masters.dark_scale(light - (b if b is not None else 0), signal)
            header["DARKSCAL"] = (round(k, 4), "dark scale that minimised the noise")
            dark_scales.append(float(k))
        if params["fix_defects"] and (d is not None or f is not None):
            defects = _defects(entry, b, d, dh, f, defect_maps, out, header)
        pattern = bayer.pattern_of(header) if params["split_colour"] else None
        data = masters.calibrate(light, exptime, b, d, dh, f, dark_factor=k, defects=None if pattern else defects)
        if pattern and defects is not None:  # fill from pixels of the same colour only
            data = bayer.repair_cfa(data, defects, masters.repair)
        _record_masters(header, entry, built, f is not None, params)
        # shortcut: lights with the same file name in different sub-folders overwrite each other; add the
        # sub-folder to the name if users keep such layouts
        stem = re.sub(r"\.(fits?|fts)(\.gz|\.fz)?$", "", Path(entry["light"]).name, flags=re.I)
        # a colour mosaic: each colour its own half-size image (cosmic rays are found per colour, after the split)
        channels = bayer.split(data, pattern).items() if pattern else [("", data)]
        for colour, plane in channels:
            h = bayer.channel_header(header, pattern, colour) if pattern else header
            cosmic = []
            if params["cosmic_rays"]:
                plane = _remove_cosmic_rays(plane, h, params["read_noise"], cosmic)
            trail, band = trails_run.search(plane, params, Path(entry["light"]).name)
            found_trails += [trail] if trail else []
            used = planes_out.used_masters(entry, built, variances, f is not None)
            path = out / f"{stem}{'_' + colour if colour else ''}.fits"
            saved = planes_out.save(path, plane, h, params, None if pattern else light, exptime, used, k, defects,
                                    cosmic[0] if cosmic else None, band)  # fmt: skip
            (arcs if entry["light"] in lamps else calibrated).append(saved)
    written = [v[2] for v in built.values()] + [str(v[1]) for v in defect_maps.values()]
    return {
        "unused_groups": [
            {"kind": k[0], "frames": len(plan.groups[k]), "file": Path(plan.groups[k][0]).name} for k in unused
        ],
        "masters": written,
        "library_used": [[Path(k[2]).name, k[0]] for k in sorted(from_library)],
        "calibrated": calibrated,
        "missing": plan.missing,
        "failed_masters": failed,
        "master_methods": methods,
        "quality": qc,
        "arcs": arcs,
        "trails": found_trails,
        "dark_scales": dark_scales,  # shown to the user: a scale far from 1 points to a wrong dark
    }


def _defects(entry, b, d, dh, f, defect_maps, out, header):
    """The hot / dead pixel map of the light's dark and flat: one per pair, saved next to the masters."""
    import numpy as np
    from astropy.io import fits

    pair = (entry["dark"], entry["flat"])
    if pair not in defect_maps:
        signal = None if d is None else d if dh.get("BIASSUB") or b is None else d - b
        bad = masters.defect_map(signal, f)
        path = out / "masters" / f"defects_{len(defect_maps):02d}.fits"
        masters.save(path, bad.astype(np.float32), fits.Header({"IMAGETYP": "Defect map", "NBAD": int(bad.sum())}))
        defect_maps[pair] = (bad, path)
    bad, path = defect_maps[pair]
    header["CALDEF"] = (path.name, f"{int(bad.sum())} hot / dead pixels repaired")
    return bad


def _save_master(out, kind, n, data, header, qc, paths, bias, var=None):
    """The master written next to the frames (with its variance as a VAR extension when given), and its quality
    report kept under its name."""
    name = f"master_{kind}_{n:02d}.fits"
    qc[name] = _quality(kind, data, header, len(paths), bias)
    return planes_out.save_master(out / "masters" / name, data, header, var)


def _quality(kind, data, header, n_inputs, bias):
    """The master's checks (calibration/quality.py, CAL-6) as plain values: {check: {value, ok, note}}."""
    from .quality import report

    known = {"n_inputs": n_inputs}
    if kind == "dark" and bias is not None:
        known |= {"bias": bias, "exptime": get(header, "EXPTIME", "EXPOSURE", default=0.0) or None,
                  "gain": get(header, "EGAIN", "GAIN", default=1.0) or 1.0}  # fmt: skip
    try:
        return {k: {"value": float(v["value"]), "ok": bool(v["ok"]), "note": v["note"]}
                for k, v in report(kind, data, **known).items()}  # fmt: skip
    except (ValueError, ZeroDivisionError):  # a tiny or odd master: no report rather than no calibration
        return {}


def _remove_cosmic_rays(data, header, read_noise, mask_out=None):
    import numpy as np

    from .cosmics import detect_cosmics  # astroscrappy's answer, its later passes only where they can differ

    gain = get(header, "EGAIN", "GAIN", default=1.0) or 1.0
    mask, clean = detect_cosmics(np.nan_to_num(data), gain=gain, readnoise=read_noise)
    if mask_out is not None:
        mask_out.append(mask)
    header["CRCLEAN"] = (int(mask.sum()), "pixels replaced by astroscrappy")
    return np.where(np.isnan(data), np.nan, clean).astype(np.float32)


@step("stacking.drizzle", inputs=("images", "output"), outputs=("stack",), scale=2, pixfrac=0.6)
def drizzle_step(inputs, params, ctx):
    """Dithered, undersampled frames onto a finer grid (see calibration/drizzle.py); weights as extension 2."""
    from astropy.io import fits

    from .. import timing
    from .drizzle import drizzle, scaled_header
    from .stacking import align_offsets

    paths = timing.chronological(inputs["images"])
    offsets = align_offsets(paths, ctx)
    ctx.progress(0.4, "drizzle")
    image, weight = drizzle((masters.load(p)[0] for p in paths), offsets, params["scale"], params["pixfrac"])
    header = scaled_header(masters.load(paths[0])[1], params["scale"])
    header["NCOMBINE"] = (len(paths), "frames drizzled")
    header["DRIZSCAL"], header["DRIZPIXF"] = (params["scale"], "output pixels per input pixel"), params["pixfrac"]
    provenance.to_fits(header, provenance.record("stacking.drizzle", params, {"images": paths}))
    write_fits(
        [fits.PrimaryHDU(image, header), fits.ImageHDU(weight, name="WEIGHT")],
        inputs["output"],
        output_verify="silentfix",
    )
    return {"stack": str(inputs["output"])}


@step(
    "stacking.stack",
    inputs=("images", "output"),
    outputs=("stack",),
    sigma=3.0,
    method="mean",
    rejection="sigma",
    low=1,
    high=1,
    normalize="none",
    weighting="none",
    align="translation",
    align_stars=(),
)
def stack_step(inputs, params, ctx):
    """Calibrated frames aligned and combined into one image (mean or median, with rejection); the coverage as a
    second extension."""
    from .. import timing
    from .stacking import save_stack, stack

    keys = ("sigma", "method", "rejection", "low", "high", "normalize", "weighting", "align", "align_stars")
    image, coverage, header = stack(timing.chronological(inputs["images"]), ctx=ctx, **{k: params[k] for k in keys})
    provenance.to_fits(header, provenance.record("stacking.stack", params, {"images": list(inputs["images"])}))
    return {"stack": save_stack(inputs["output"], image, coverage, header)}


from . import step_params  # noqa: E402, F401  (the settings described, AUT-1.2; after the steps exist)
