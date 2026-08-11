"""Calibration as engine steps (run in worker processes, recorded in the project)."""

import re
from pathlib import Path

from .. import __version__
from ..engine.steps import step
from ..hdr import get
from ..io import bayer
from . import masters
from .frames import Frame, scan
from .matching import best_bias, best_dark, group_key, make_plan


@step(
    "calibration.scan",
    inputs=("folder",),
    outputs=("frames", "problems", "raw_converted"),
    optional=("lights",),
    clock_utc_offset=0.0,
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
        raise ValueError(f"folder not found: {inputs.get('folder') or ''}")  # nothing given: said like a wrong one
    for folder in folders + light_dirs:
        if not Path(folder).is_dir():
            raise ValueError(f"folder not found: {folder}")
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
    return {
        "frames": [frames[p].as_dict() for p in sorted(frames)],
        "problems": problems,
        "raw_converted": len(raw),
    }


def _frame_header(path):
    """The header that describes the image of a frame (the primary's keywords included, as read_frame reads it)."""
    from astropy.io import fits

    from ..io.fits import find_image_hdu, inherited

    with fits.open(path) as hdul:
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
    outputs=("masters", "calibrated", "missing", "failed_masters", "arcs", "dark_scales"),
    sigma=3.0,
    temp_tol=2.0,
    cosmic_rays=False,
    read_noise=10.0,
    optimize_dark=False,
    fix_defects=False,
    divide_flat=True,
    split_colour=True,
    linearity=(),
)
def run_step(inputs, params, ctx):
    """Build every master the plan needs, then calibrate every light. Missing corrections are skipped and listed.
    linearity: coefficients c0, c1, c2... of the camera's linearity correction (masters.linearity), or empty."""
    with masters.linearity(params["linearity"]):
        return _run(inputs, params, ctx)


def _run(inputs, params, ctx):
    import numpy as np
    from astropy.io import fits

    frames = _frames(inputs["frames"])
    plan = make_plan(frames, params["temp_tol"])
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
    unused = _unused_groups(plan, reps, temp_tol)  # e.g. full-chip bias next to the cropped lights' (real LCO night)
    order = sorted(
        (k for k in plan.groups if k not in unused), key=lambda k: ("bias", "dark", "flat").index(kinds[k])
    )  # flats need bias + dark
    failed = []  # masters that could not be made: their frames are left out, the lights calibrated without them
    for n, key in enumerate(order):
        ctx.check()
        ctx.progress(0.5 * n / max(1, len(order)), f"master {kinds[key]}")
        paths, rep = plan.groups[key], reps[key]
        bias = best("bias", rep)[0]
        try:
            if kinds[key] == "bias":
                data, h = masters.master_bias(paths, params["sigma"])
            elif kinds[key] == "dark":
                data, h = masters.master_dark(paths, bias, params["sigma"])
            else:  # no matching dark is fine for flats: they are bright, dark current is < 0.1 % of them
                dark, dh, _ = best("dark", rep)
                data, h = masters.master_flat(paths, bias, dark, dh, params["sigma"])
        except masters.CalibrationError as e:  # one bad group (e.g. flats that are not flats) must not stop the night
            failed.append({"kind": kinds[key], "frames": len(paths), "file": Path(paths[0]).name, "reason": str(e)})
            continue
        name = f"master_{kinds[key]}_{n:02d}.fits"
        built[key] = (data, h, masters.save(out / "masters" / name, data, h))

    calibrated, arcs, defect_maps, dark_scales = [], [], {}, []
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
            pair = (entry["dark"], entry["flat"])
            if pair not in defect_maps:  # one map per dark / flat pair, saved next to the masters
                signal = None if d is None else d if dh.get("BIASSUB") or b is None else d - b
                bad = masters.defect_map(signal, f)
                path = out / "masters" / f"defects_{len(defect_maps):02d}.fits"
                masters.save(
                    path, bad.astype(np.float32), fits.Header({"IMAGETYP": "Defect map", "NBAD": int(bad.sum())})
                )
                defect_maps[pair] = (bad, path)
            defects, path = defect_maps[pair]
            header["CALDEF"] = (path.name, f"{int(defects.sum())} hot / dead pixels repaired")
        pattern = bayer.pattern_of(header) if params["split_colour"] else None
        data = masters.calibrate(light, exptime, b, d, dh, f, dark_factor=k, defects=None if pattern else defects)
        if pattern and defects is not None:  # fill from pixels of the same colour only
            data = bayer.repair_cfa(data, defects, masters.repair)
        for kind in ("bias", "dark", "flat"):
            used = built[entry[kind]][2] if entry[kind] and (kind != "flat" or f is not None) else "none"
            header[f"CAL{kind[0].upper()}"] = (Path(used).name, f"{kind} used for calibration")
        header.add_history(f"calibrated by astrowb {__version__}")
        # shortcut: lights with the same file name in different sub-folders overwrite each other; add the
        # sub-folder to the name if users keep such layouts
        stem = re.sub(r"\.(fits?|fts)(\.gz|\.fz)?$", "", Path(entry["light"]).name, flags=re.I)
        # a colour mosaic: each colour its own half-size image (cosmic rays are found per colour, after the split)
        channels = bayer.split(data, pattern).items() if pattern else [("", data)]
        for colour, plane in channels:
            h = bayer.channel_header(header, pattern, colour) if pattern else header
            if params["cosmic_rays"]:
                plane = _remove_cosmic_rays(plane, h, params["read_noise"])
            saved = masters.save(out / f"{stem}{'_' + colour if colour else ''}.fits", plane, h)
            (arcs if entry["light"] in lamps else calibrated).append(saved)
    written = [v[2] for v in built.values()] + [str(v[1]) for v in defect_maps.values()]
    return {
        "unused_groups": [
            {"kind": k[0], "frames": len(plan.groups[k]), "file": Path(plan.groups[k][0]).name} for k in unused
        ],
        "masters": written,
        "calibrated": calibrated,
        "missing": plan.missing,
        "failed_masters": failed,
        "arcs": arcs,
        "dark_scales": dark_scales,  # shown to the user: a scale far from 1 points to a wrong dark
    }


def _remove_cosmic_rays(data, header, read_noise):
    import astroscrappy
    import numpy as np

    gain = get(header, "EGAIN", "GAIN", default=1.0) or 1.0
    mask, clean = astroscrappy.detect_cosmics(np.nan_to_num(data), gain=gain, readnoise=read_noise)
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
    header.add_history(f"drizzled by astrowb {__version__}")
    fits.HDUList([fits.PrimaryHDU(image, header), fits.ImageHDU(weight, name="WEIGHT")]).writeto(
        inputs["output"], overwrite=True, output_verify="silentfix"
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
)
def stack_step(inputs, params, ctx):
    from .. import timing
    from .stacking import save_stack, stack

    keys = ("sigma", "method", "rejection", "low", "high", "normalize", "weighting", "align")
    image, coverage, header = stack(timing.chronological(inputs["images"]), ctx=ctx, **{k: params[k] for k in keys})
    header.add_history(f"stacked by astrowb {__version__}")
    return {"stack": save_stack(inputs["output"], image, coverage, header)}
