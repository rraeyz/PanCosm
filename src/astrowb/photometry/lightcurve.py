"""Differential light curve of one target against an ensemble of comparison stars.

rel_flux = F_target / sum(F_comp);  relative error from the propagated flux errors:
    (s_rel / rel)^2 = (s_t / F_t)^2 + sum(s_c^2) / (sum F_c)^2
Times are mid-exposure; BJD_TDB when the target's sky position is known, else JD_UTC.
"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord

from .. import timing
from ..calibration.masters import load
from ..hdr import get, number
from ..io import tpf
from ..io.inspect import saturation_level
from .aperture import (
    choose_apertures,
    frame_shift,
    measure,
    measure_cube,
    recenter,
    scintillation,
    seeing_fwhm,
)
from .differential import ensemble
from .psf import neighbours_setup


def target_coord(header, given: str | None = None) -> SkyCoord | None:
    """Sky position: the user's value, else OBJCTRA/OBJCTDEC, else RA/DEC from the header."""
    if given:
        return SkyCoord(given, unit=(u.hourangle, u.deg))
    for ra_key, dec_key in (("OBJCTRA", "OBJCTDEC"), ("RA", "DEC")):
        if ra_key in header and dec_key in header:
            ra, dec = header[ra_key], header[dec_key]
            try:
                if isinstance(ra, str) and any(c in ra.strip() for c in ": hH"):  # '13:39:01.3', '13 39 01'
                    return SkyCoord(ra, dec, unit=(u.hourangle, u.deg))
                return SkyCoord(number(ra) * u.deg, number(dec) * u.deg)  # degrees, also written as text
            except (TypeError, ValueError):  # unreadable: the next pair, else the user types the position
                continue
    return None


def light_curve(
    paths,
    target_xy,
    comps_xy,
    r_ap,
    r_in,
    r_out,
    coord: str | None = None,
    gain=None,
    box=11,
    ctx=None,
    auto=False,
    follow_seeing=False,
    extra_xy=(),
    psf=False,
    aperture_m=None,
    ref_path=None,
    camera=None,
    sky_method="median",
    fixed=(),
    header_time="auto",
    shutter_delay=0.0,
    apertures=(),
    remove_neighbours=False,
    centring="auto",
    track_stars=(),
) -> dict:
    """Positions are 0-based (x, y) pixels in the first frame. Returns plain lists (JSON-friendly).
    auto: the three radii are chosen from the stars on the first frame (aperture.choose_apertures).
    follow_seeing: on every frame the radii are scaled by that frame's FWHM over the first frame's, so the
    aperture holds the same part of the light when the seeing changes (a "variable aperture").
    extra_xy: further stars (other targets, check stars) measured against the same comparison ensemble.
    remove_neighbours: stars near the measured ones are fitted and subtracted before the apertures (psf.py).
    psf: fluxes from PSF fits of each frame's FWHM (crowded fields, fieldstars.psf_measure) instead of apertures.
    aperture_m: telescope aperture (m) for the scintillation noise added to every flux error (aperture.scintillation);
    by default from APTDIA (mm) in the header. Without an aperture, the site or the target position no
    scintillation is added and "scintillation" in the result is None.
    ref_path: the frame the positions were marked on, when not the first in time: they are re-centred there and
    carried to the first frame by the shift between the two (as between consecutive frames).
    camera: {"read_noise": e-, "dark": e- per pixel per second}: the sky noise of every pixel from the camera's numbers
    and the sky level, as AstroImageJ (Collins et al. 2017, appendix B), instead of the scatter measured in the sky
    ring (aperture.measure).
    sky_method: the sky estimate (aperture.sky_estimate); centring: auto, moments, gauss or none (aperture.recenter);
    track_stars: stars picked on the first frame that place every frame (shift, rotation; stacking.picked_transforms).
    fixed: indices of stars (0 the target, then comparisons, then extra stars) that are not re-centred but follow the
    field: the median shift the centred stars took on that frame (AstroImageJ's per-aperture centroid off; a faint
    star beside a bright one is not pulled onto it).
    header_time, shutter_delay: what the header's time marks ("auto", "start", "mid", "end") and the camera's shutter
    delay in seconds (timing.mid_time); the result also has "hjd_utc" when the target's position is known."""
    paths = [str(p) for p in paths]
    stars0 = np.array([target_xy, *comps_xy, *extra_xy], dtype=float)
    n_comp = len(comps_xy)
    ref, h0 = load(paths[0])
    # given positions centred once within half the box (a click 2.7 px off Qatar-1 left the aperture off the star);
    # clicks farther off are put on their star by the window (snap_click): a faint target beside a bright one stays
    if ref_path and str(ref_path) != paths[0]:
        marked = load(ref_path)[0]
        stars0 = recenter(marked, stars0, box, max_move=box / 2)
        stars0 = stars0 + frame_shift(marked, ref, 2 if ref.size > 4e6 else 1)
    clicked = stars0.copy()
    stars0 = recenter(ref, stars0, box, max_move=box / 2)
    fixed = [k for k in fixed if 0 <= k < len(stars0)]
    stars0[fixed] = clicked[fixed]  # a star that follows the field keeps the place it was marked at
    opts = {"camera": camera, "sky_method": sky_method, "fixed": tuple(fixed), "time": (header_time, shutter_delay),
            "centring": centring, "apertures": tuple(float(r) for r in apertures if 0 < r < r_in)}  # fmt: skip
    sky = target_coord(h0, coord)
    where = timing.location(h0)
    g = float(gain or get(h0, "EGAIN", "GAIN", default=1.0) or 1.0)
    rows = []
    chosen = None
    # a small stamp (a TESS pixel file is 11 x 11 px) holds no ring of the default radii: every flux came out NaN
    too_big = r_in >= 0.5 * min(ref.shape[-2:])
    if auto or too_big:
        chosen = choose_apertures(ref, stars0[: 1 + n_comp], g) | {"replaced": bool(too_big and not auto)}
        r_ap, r_in, r_out = chosen["r_ap"], chosen["r_in"], chosen["r_out"]
        opts["apertures"] = tuple(r for r in opts["apertures"] if r < r_in)
    fwhm0 = seeing_fwhm(ref, recenter(ref, stars0, box)) if follow_seeing else None
    opts["neighbours"] = neighbours_setup(ref, stars0, n_comp, r_out) if remove_neighbours and not psf else None
    radii, fwhms, peaks = [], [], []
    saturation = saturation_level(h0, ref)
    src = None if psf or follow_seeing or remove_neighbours else tpf.source(paths)
    if src is not None:  # the cadences of a TESS / Kepler pixel file: measured at once, the stars do not move
        rows, peaks, radii, src_times = _pixel_file_rows(src, paths, stars0, (r_ap, r_in, r_out), g, box)
    binning = 2 if ref.size > 4e6 else 1  # large frames: the shift from 2x2-binned frames, then re-centred anyway
    from ..engine.parallel import pmap, workers

    parallel = src is None and workers() > 1 and len(paths) >= 24
    from ..calibration.stacking import align_offsets, picked_transforms

    placed = [stars0 @ m.T + t for m, t in picked_transforms(paths, track_stars, ctx)] if len(track_stars) else None
    if parallel:  # every frame on its own core: the shifts first (between consecutive frames, also in parallel),
        # then each frame read, re-centred from the shifted positions and measured where it is read
        placed = placed or [stars0 + off for off in np.asarray(align_offsets(paths, ctx, binning))]
        jobs = [(p, pred, stars0, (r_ap, r_in, r_out), g, box, fwhm0, psf, n_comp, paths[0], opts)
                for p, pred in zip(paths, placed, strict=True)]  # fmt: skip
        for row, peak, rad, f in pmap(_frame, jobs, ctx, "photometry"):
            rows.append(row)
            peaks.append(peak)
            radii.append(rad)
            if fwhm0:
                fwhms.append(f)
    reader = ThreadPoolExecutor(1)  # the next frame is read (and decompressed) while this one is measured
    serial = src is None and not parallel
    upcoming = reader.submit(load, paths[1]) if len(paths) > 1 and serial else None
    for i, p in enumerate(paths if serial else []):
        if ctx:
            ctx.check()
            ctx.progress(i / len(paths), "photometry")
        if i:
            data, h = upcoming.result()
            upcoming = reader.submit(load, paths[i + 1]) if i + 1 < len(paths) else None
        else:
            data, h = ref, h0
        # every frame is placed against the first, never against the previous one: a frame tracked wrongly (a cloud,
        # a jolt) took every later frame with it, and the apertures measured empty sky without a word (owner's
        # NY Vir night); the stars found are then checked, and a star pattern match tried when they are not there
        shift = np.zeros(2) if i == 0 or placed else np.asarray(frame_shift(ref, data, binning))
        pred = placed[i] if placed else stars0 + shift
        xy, flux, err, skylev, r, f, multi, lost = _measure_frame(
            data, h, pred, stars0, (r_ap, r_in, r_out), g, box, fwhm0, psf, n_comp, paths[0], opts=opts
        )
        if fwhm0:
            fwhms.append(f)
        radii.append(r)
        peaks.append(_peaks(data, xy, r[0]))
        try:
            t = timing.mid_time(h, *opts["time"])
        except timing.TimeError:  # no time in the file (a screenshot, a converted picture): the frame order
            t = None
        moved = np.hypot(*(xy - pred).T)  # how far centring moved each star from where the frame's placing put it
        rows.append((p, t, flux, err, skylev, xy, get(h, "EXPTIME", "EXPOSURE", default=0.0), lost, moved, multi))
    reader.shutdown(wait=False)

    def comps_seen(r):  # which comparison stars the frame has (signal above SNR_FOUND)
        f, e = np.asarray(r[2][1 : 1 + n_comp], float), np.asarray(r[3][1 : 1 + n_comp], float)
        return np.divide(f, e, out=np.zeros_like(f), where=e > 0) >= SNR_FOUND

    # a frame without some comparison stars is kept with the ones it has (item 13), when it still has one
    partial = {k for k, r in enumerate(rows) if r[7] and r[7][0] == "comparison" and comps_seen(r).any()}
    gone = [(Path(r[0]).name, *r[7]) for k, r in enumerate(rows) if r[7] and k not in partial]
    keep = [k for k, r in enumerate(rows) if not r[7] or k in partial]
    missing = {k: np.flatnonzero(~comps_seen(rows[k])) for k in partial}
    if not keep:
        raise ValueError(
            "the target or a comparison star was not found on any frame: check the stars marked on the first frame"
        )
    missing = [missing.get(k, []) for k in keep]
    rows, peaks, radii = [rows[k] for k in keep], [peaks[k] for k in keep], [radii[k] for k in keep]
    fwhms = [fwhms[k] for k in keep] if fwhms else fwhms
    if src is not None:  # the archive's BJD_TDB as it is, and its UTC from the file (no conversion per cadence)
        times, tvals, scale = src_times[1], src_times[0], "BJD_TDB"
    elif any(r[1] is None for r in rows):  # without times the light curve is against the frame number
        times, tvals, scale = None, np.arange(len(rows), dtype=float), "frame number"
    else:
        times = timing.Time([r[1] for r in rows])
        if sky is not None:
            tvals, scale = timing.bjd_tdb(times, sky, where).jd, "BJD_TDB"
        else:
            tvals, scale = times.utc.jd, "JD_UTC"
    flux = np.array([r[2] for r in rows], float)
    err = np.array([r[3] for r in rows], float)
    for i, ks in enumerate(missing):  # not there: no flux, rather than the sky's noise
        flux[i, 1 + np.asarray(ks, int)] = err[i, 1 + np.asarray(ks, int)] = np.nan
    known = times is not None and where is not None and sky is not None
    airmass = [timing.airmass(t, sky, where) for t in times] if known else None
    if aperture_m is None and get(h0, "APTDIA"):
        aperture_m = get(h0, "APTDIA") / 1000.0  # APTDIA is in millimetres (MaxIm DL, SGP, NINA)
    scint = None
    exptimes = np.array([r[6] for r in rows])
    if aperture_m and airmass is not None and (exptimes > 0).all():
        scint = scintillation(aperture_m, 1.0, airmass, where.height.to_value("m")) / np.sqrt(exptimes)
        err = np.sqrt(err**2 + (scint[:, None] * flux) ** 2)  # independent of photon and sky noise
    cf, ce = flux[:, 1 : 1 + n_comp], err[:, 1 : 1 + n_comp]
    rel, rel_err = ensemble(flux[:, 0], err[:, 0], cf, ce)
    out = {
        "file": [Path(r[0]).name for r in rows],
        "time": tvals.tolist(),
        "time_scale": scale,
        "jd_utc": times.utc.jd.tolist() if times is not None else [float("nan")] * len(rows),  # AAVSO wants JD UTC
        # HJD (UTC): much of the eclipsing-binary O−C literature (item 14)
        "hjd_utc": timing.hjd(times, sky, where).jd.tolist() if times is not None and sky is not None else None,
        "rel_flux": rel.tolist(),
        "rel_flux_err": rel_err.tolist(),
        "target_flux": flux[:, 0].tolist(),
        "target_flux_err": err[:, 0].tolist(),
        "comp_flux": cf.tolist(),
        "comp_flux_err": ce.tolist(),
        "peak": [p for p, _ in peaks],  # brightest pixel in each star's aperture (target, comparisons, extra stars)
        "flags": [f for _, f in peaks],  # per frame and star: C a spike (cosmic ray, hot pixel), E off the edge
        "saturation": saturation,
        "exptime": [float(e) for e in exptimes],  # per frame: the cloud check compares counts per second
        "sky": [r[4].tolist() for r in rows],
        "xy": [r[5].tolist() for r in rows],
        "coord": sky.to_string("hmsdms") if sky is not None else None,
        "radii": radii,  # aperture, inner and outer sky radius used on each frame (pixels)
        # how far centring moved each star from where the frame's shift put it (pixels; item 5)
        "centring_move": [r[8].tolist() if len(r) > 8 else [0.0] * len(r[5]) for r in rows],
        "fixed": list(opts["fixed"]) if src is None else [],
        "scintillation": None if scint is None else scint.tolist(),  # relative, per frame
        "aperture_m": aperture_m,
        # frames left out, with why: {file: ["target"] / ["comparison", k] / ["aligned"]} (a dict: never taken for
        # a per-frame list by code that filters the frames)
        "lost": {x[0]: list(x[1:]) for x in gone},
        # frames measured against the comparison stars they have: {file: [1-based numbers of the missing stars]}
        "partial": {Path(r[0]).name: [int(k) + 1 for k in ks] for r, ks in zip(rows, missing, strict=True) if len(ks)},
    }
    if chosen:
        out["apertures"] = chosen
    if (by := _by_aperture(opts, [r[9] if len(r) > 9 else None for r in rows], scint)) is not None:
        out["by_aperture"] = by  # item 10: choose the radius later, no measuring
    if fwhms:
        out["fwhm"] = fwhms
    if len(extra_xy):
        out["extra_flux"] = flux[:, 1 + n_comp :].tolist()
        out["extra_flux_err"] = err[:, 1 + n_comp :].tolist()
    if airmass is not None:
        out["airmass"] = airmass
    return out


def _by_aperture(opts, multi, scint):
    """The several radii's fluxes and errors, the scintillation added to every radius as to the main aperture."""
    if not opts["apertures"] or any(m is None for m in multi):
        return None
    if scint is not None:
        multi = [np.array([m[0], np.sqrt(m[1] ** 2 + (s * m[0]) ** 2)]) for m, s in zip(multi, scint, strict=True)]
    return {"radii": list(opts["apertures"]), "flux": [m[0].tolist() for m in multi],
            "err": [m[1].tolist() for m in multi]}  # fmt: skip


def _frame(job):
    """One frame of light_curve's parallel path: read, re-centred from the predicted positions, measured, checked."""
    p, pred, stars0, radii0, g, box, fwhm0, psf, n_comp, ref_path, opts = job
    asked = np.asarray(pred, float)  # where the frame's shift put the stars, before centring
    corner, partial = np.zeros(2), False
    if psf or not np.isfinite(pred).all():
        data, h = load(p)
    else:  # only the part of the frame around the stars is read: half the time of a 2400 x 2400 fpack frame
        # margin: the widest centroid box (301 px), the sky ring with radii following the seeing (up to 5x)
        m = int(max(155, (5 if fwhm0 else 1) * radii0[2] + 30) + box)
        corner = np.maximum(0, np.floor(pred.min(axis=0)) - m)
        (x1, y1), (x0, y0) = np.ceil(pred.max(axis=0)) + m, corner
        data, h = load(p, (y0, y1, x0, x1))
        pred, partial = pred - corner, True
    out = _measure_frame(data, h, pred, stars0, radii0, g, box, fwhm0, psf, n_comp, ref_path, partial, opts)
    if out is None:  # the stars were not where the shifts put them: the whole frame, matched by its star pattern
        data, h = load(p)
        out = _measure_frame(data, h, pred + corner, stars0, radii0, g, box, fwhm0, psf, n_comp, ref_path, False, opts)
        corner = np.zeros(2)
    xy, flux, err, skylev, radii, f, multi, lost = out
    try:
        t = timing.mid_time(h, *(opts or {}).get("time", ("auto", 0.0)))
    except timing.TimeError:
        t = None
    moved = np.hypot(*(xy + corner - asked).T)
    row = (p, t, flux, err, skylev, xy + corner, get(h, "EXPTIME", "EXPOSURE", default=0.0), lost, moved, multi)
    return row, _peaks(data, xy, radii[0]), radii, f


SNR_FOUND = 3.0  # a star whose flux is below 3 sigma of its noise is not there (empty sky, clouds)
_REF_STARS = {}  # reference frame -> its bright stars, for star-pattern matching (once per process)


def _ref_stars(ref_path):
    from ..calibration import starmatch

    if _REF_STARS.get("path") != ref_path:
        _REF_STARS.update(path=ref_path, xy=starmatch.stars(load(ref_path)[0]))
    return _REF_STARS["xy"]


def _measure_frame(data, h, pred, stars0, radii0, g, box, fwhm0, psf, n_comp, ref_path, partial=False, opts=None):
    """Centre, measure and check the stars of one frame from their predicted positions (the reference frame's
    positions stars0 moved by the frame's shift). When the target or a comparison star is not found there, the frame
    is matched to the reference by its star pattern (a wrong shift, a large jump, rotation: a meridian flip) and
    measured again; a frame read in part (partial) returns None instead, to be read whole. Returns positions, fluxes,
    errors, sky, radii, FWHM and why the frame is left out: () when it is good, ("target",) when the target is not
    there, ("comparison", k) for comparison star k (1-based), ("aligned",) when the frame could not be placed."""
    from ..calibration import starmatch

    out = _measure_at(data, h, pred, radii0, g, box, fwhm0, psf, n_comp, opts)
    lost = _lost(out, n_comp)
    if lost:
        off = _field_offset(data, pred, box)
        if off is not None:  # the shifts added up over the night put the stars a few pixels off (item 9b)
            again = _measure_at(data, h, pred + off, radii0, g, box, fwhm0, psf, n_comp, opts)
            if _rank(_lost(again, n_comp)) < _rank(lost):
                out, lost = again, _lost(again, n_comp)
    if lost:
        if partial:
            return None
        try:
            m, t, _, _ = starmatch.match(_ref_stars(ref_path), starmatch.stars(data))
            again = _measure_at(data, h, np.asarray(stars0) @ m.T + t, radii0, g, box, fwhm0, psf, n_comp, opts)
            if _rank(_lost(again, n_comp)) < _rank(lost):
                out, lost = again, _lost(again, n_comp)
        except ValueError:  # no pattern to match (clouds, an empty frame): left as it is
            pass
    return (*out[:-1], lost)


def _field_offset(data, pred, box):
    """The median offset of the stars from where they were predicted, found in a search three times as wide, or None
    when fewer than two stars are found: a few pixels of error in the predicted positions (frame-to-frame shifts added
    up over hundreds of frames) cost a centring pass here instead of reading the whole frame and matching its star
    pattern (ten times slower; plans/photometry.md item 9b)."""
    wide = 3 * box // 2 * 2 + 1
    pred = np.asarray(pred, float)
    off = np.zeros(2)
    for _ in range(3):  # a star near the edge of the wide box is found only part of the way: search again from there
        xy, found = recenter(data, pred + off, box=wide, max_move=wide / 2, found=True)
        if found.sum() < min(2, len(pred)):
            return None if not off.any() else off
        step = np.median(xy[found] - (pred + off)[found], axis=0)
        off = off + step
        if np.hypot(*step) < 0.5:
            break
    return off


def _lost(out, n_comp):
    """Why a measured frame cannot be used, () when it can (see _measure_frame)."""
    xy, flux, err, skylev, radii, f, _, found = out
    n_main = 1 + n_comp
    if found[:n_main].mean() < 0.5:  # most stars are not where they were looked for: the frame is not placed
        return ("aligned",)
    snr = np.divide(flux, err, out=np.zeros_like(flux), where=err > 0)
    if not snr[0] >= SNR_FOUND:
        return ("target",)
    for k in range(1, n_main):
        if not snr[k] >= SNR_FOUND:
            return ("comparison", k)
    return ()


JUMP_PX = 1.5


def _off_the_field(xy, pred, found):
    """A star whose centroid moved more than JUMP_PX away from the move the other stars took (a faint target pulled
    onto a noise peak: a running stack of PHO-42 lost 60 % of its light that way) follows the field instead."""
    move = xy - pred
    ok = np.flatnonzero(found)
    if len(ok) < 3:
        return xy
    field = np.median(move[ok], axis=0)
    off = np.hypot(*(move - field).T) > JUMP_PX
    if off.any() and (~off[ok]).sum() >= 2:
        xy = xy.copy()
        xy[off] = pred[off] + field
    return xy


def _rank(lost):
    """Lower is better: a good frame, then one comparison star missing, then the target, then not placed."""
    return {(): 0, "comparison": 1, "target": 2, "aligned": 3}[lost[0] if lost else ()]


def _measure_at(data, h, pred, radii0, g, box, fwhm0, psf, n_comp, opts=None):
    """Centroids from the predicted positions, then the fluxes (apertures or PSF); found: centroid near the
    prediction. opts: {"camera", "sky_method", "fixed"} (light_curve)."""
    opts = opts or {}
    camera, sky_method = opts.get("camera"), opts.get("sky_method", "median")
    r_ap, r_in, r_out = radii0
    xy, found = recenter(data, pred, box, found=True, method=opts.get("centring", "auto"))
    xy = _off_the_field(xy, pred, found)
    fixed = [k for k in opts.get("fixed", ()) if k < len(xy)]
    if fixed:  # these follow the field: the prediction moved by the median shift of the centred stars
        free = [k for k in range(len(xy)) if k not in fixed and found[k]]
        move = np.median(xy[free] - pred[free], axis=0) if free else np.zeros(2)
        xy[fixed], found[fixed] = pred[fixed] + move, True
    k, f = 1.0, None
    if fwhm0:
        f = seeing_fwhm(data, xy)
        k = f / fwhm0 if np.isfinite(f) and 0.2 < f / fwhm0 < 5 else 1.0  # a failed measurement keeps the radii
    radii = [r_ap * k, r_in * k, r_out * k]
    if psf:
        from .fieldstars import psf_measure

        f_psf = f if f is not None else seeing_fwhm(data, xy[: 1 + n_comp])
        flux, err, skylev = psf_measure(data, xy, f_psf if np.isfinite(f_psf) else r_ap / 1.5, *radii[1:], g)
    else:
        sky_mask = None
        if opts.get("neighbours") is not None:
            from .psf import remove_neighbours

            f_now = f if f is not None else seeing_fwhm(data, xy[: 1 + n_comp])
            data, sky_mask = remove_neighbours(
                data, pred, f_now, *opts["neighbours"]
            )  # a centroid is pulled by the neighbour
            xy[~np.isin(np.arange(len(xy)), fixed)] = recenter(data, pred, box)[~np.isin(np.arange(len(xy)), fixed)]
        cam = None
        if camera:  # dark current over this frame's exposure
            exptime = get(h, "EXPTIME", "EXPOSURE", default=0.0) or 0.0
            cam = (float(camera.get("read_noise", 0.0)), float(camera.get("dark", 0.0)) * exptime)
        flux, err, skylev = measure(data, xy, *radii, g, h.get("PIXNOISE"), cam, sky_method, sky_mask)
    multi = None
    if opts.get("apertures") and not psf:  # item 10: every radius asked for, the same sky ring, kept to choose later
        rs = [r * k for r in opts["apertures"]]
        both = [measure(data, xy, r, *radii[1:], g, h.get("PIXNOISE"), cam, sky_method, sky_mask)[:2] for r in rs]
        multi = np.array([[fl for fl, _ in both], [e for _, e in both]])  # (flux / error, radius, star)
    return xy, flux, err, skylev, radii, f, multi, found


def _pixel_file_rows(src, paths, stars0, radii, gain, box):
    """The per-frame rows of light_curve for the cadences of one pixel file, measured all at once with fixed
    apertures, as the SPOC pipeline and lightkurve do: on a real TESS file (WASP-12, sector 20) re-centring every
    cadence moved the aperture onto the star's wings and a neighbour (x from 5.0 to 7.0 px), 216 of 16 942 cadences
    5 % off, and took 224 s; the stars are centred once, on the median of the cadences."""
    from ..io import tpf

    data, noise, bjd, utc, exptime = tpf.cube(*src)
    still = np.median(data[:: max(1, len(data) // 200)], axis=0)
    xy = recenter(still, stars0, box)
    flux, err, sky, peak = measure_cube(data, xy, *radii, gain, noise)
    rows = [(p, None, flux[i], err[i], sky[i], xy, exptime, ()) for i, p in enumerate(paths)]
    return rows, [(p, [""] * len(p)) for p in peak.tolist()], [list(radii)] * len(paths), (bjd, utc)


def _peaks(data, xy, r_ap):
    """(brightest pixel inside each aperture, for saturation warnings; the letters of what spoils it, flags.py)."""
    from photutils.aperture import ApertureStats, CircularAperture

    from .flags import aperture_flags

    peak = np.atleast_1d(ApertureStats(np.asarray(data), CircularAperture(xy, r=r_ap)).max).tolist()  # no float copy
    return peak, aperture_flags(data, xy, r_ap)


def normalise(rel, mask=None):
    """Divide by the median of the points in mask (e.g. out-of-transit), all points if None."""
    rel = np.asarray(rel, dtype=float)
    return rel / np.nanmedian(rel if mask is None else rel[mask])


def aperture_scan(paths, stars_xy, fwhm, gain=1.0, factors=(1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0), r_in=None,
                  max_frames=40, ctx=None):  # fmt: skip
    """The aperture radius that gives the steadiest light curve: on up to max_frames frames spread over the series,
    each placed against the first (as light_curve), the target over the sum of the comparison stars is measured
    through apertures of factors x fwhm and one sky ring outside the wings (from r_in, 8 times the largest aperture's
    area), and the point-to-point scatter (robust: an eclipse or a trend does not count, one bad frame neither) is
    compared. The radius that keeps most of the light usually wins over the one that is best for a single star's
    noise: when the seeing changes, a small aperture loses a different share of each star's light (owner's NY Vir
    frames: 68-80 % of the light at 1.3 FWHM, and the shares moved with the seeing).
    Returns {"radii", "scatter" (relative, per radius), "best", "r_in", "r_out", "frames"}."""
    paths = [str(p) for p in paths]
    # pairs of consecutive frames spread over the series: the star hardly changes between two frames in a row, so
    # their difference is the measurement's own noise, not the eclipse
    starts = np.unique(np.linspace(0, len(paths) - 2, max(1, min(max_frames // 2, len(paths) - 1))).round().astype(int))
    pick = np.unique(np.r_[starts, starts + 1])
    radii = np.array(factors) * fwhm
    r_in = max(r_in or 0.0, 4.5 * fwhm, radii[-1] + 2.0)
    r_out = float(np.sqrt(r_in**2 + 8.0 * radii[-1] ** 2))
    ref, _ = load(paths[0])
    stars0 = recenter(ref, np.asarray(stars_xy, float), 11, max_move=5.5)
    binning = 2 if ref.size > 4e6 else 1
    rel = {}
    for k, i in enumerate(pick):
        if ctx:
            ctx.check()
            ctx.progress(k / len(pick), "photometry")
        data = ref if i == 0 else load(paths[i])[0]
        shift = np.zeros(2) if i == 0 else np.asarray(frame_shift(ref, data, binning))
        xy, found = recenter(data, stars0 + shift, 11, found=True)
        row = []
        for r in radii:
            flux, err, _ = measure(data, xy, r, r_in, r_out, gain)
            row.append(flux[0] / flux[1:].sum() if len(flux) > 1 else flux[0])
        rel[i] = row if found.all() else None  # a frame without every star (clouds) says nothing about the aperture
    pairs = [(rel[i], rel[i + 1]) for i in starts if rel.get(i) is not None and rel.get(i + 1) is not None]
    if len(pairs) < 2:
        raise ValueError("too few frames with every star found to compare apertures")
    a, b = (np.array(x) for x in zip(*pairs, strict=True))
    p2p = 1.4826 * np.nanmedian(np.abs(b / a - 1), axis=0) / np.sqrt(2)
    best_i = int(np.nanargmin(p2p))
    near = np.flatnonzero(p2p <= 1.03 * p2p[best_i])  # within 3 %: the largest, which follows seeing changes best
    best = float(radii[near.max()])
    return {"radii": radii.tolist(), "scatter": p2p.tolist(), "best": best, "r_in": float(r_in), "r_out": r_out,
            "frames": 2 * len(pairs)}  # fmt: skip


def with_aperture(lc, i):
    """The light curve as if measured through radius lc["by_aperture"]["radii"][i] (plans/photometry.md item 10): the
    fluxes of that radius, measured with the same centres and sky, and the relative flux formed again; stars a frame
    did not have (item 13) stay out. Nothing is measured again."""
    by = lc["by_aperture"]
    f, e = np.asarray(by["flux"], float)[:, i, :], np.asarray(by["err"], float)[:, i, :]
    n_comp = np.asarray(lc["comp_flux"], float).reshape(len(f), -1).shape[1]
    gone = ~np.isfinite(np.asarray(lc["comp_flux"], float).reshape(len(f), -1))
    cf, ce = f[:, 1 : 1 + n_comp].copy(), e[:, 1 : 1 + n_comp].copy()
    cf[gone] = ce[gone] = np.nan
    rel, rel_err = ensemble(f[:, 0], e[:, 0], cf, ce)
    scale = by["radii"][i] / lc["radii"][0][0] if lc.get("radii") else 1.0
    out = dict(lc) | {
        "target_flux": f[:, 0].tolist(), "target_flux_err": e[:, 0].tolist(), "comp_flux": cf.tolist(),
        "comp_flux_err": ce.tolist(), "rel_flux": rel.tolist(), "rel_flux_err": rel_err.tolist(),
        "radii": [[r[0] * scale, *r[1:]] for r in lc.get("radii") or []],
    }  # fmt: skip
    if lc.get("extra_flux") is not None and f.shape[1] > 1 + n_comp:
        out["extra_flux"], out["extra_flux_err"] = f[:, 1 + n_comp :].tolist(), e[:, 1 + n_comp :].tolist()
    return out


def aperture_correction(lc):
    """Curve of growth from the radii measured (item 10): for each radius, the median over frames and comparison
    stars of the flux through it over the flux through the largest, and the aperture correction in magnitudes
    (-2.5 log10 of that share: add it to a magnitude measured through the radius to have the light through the
    largest). Returns {"radii", "share", "correction_mag"}."""
    by = lc["by_aperture"]
    f = np.asarray(by["flux"], float)
    n_comp = np.asarray(lc["comp_flux"], float).reshape(len(f), -1).shape[1]
    stars = f[:, :, 1 : 1 + n_comp] if n_comp else f[:, :, :1]
    with np.errstate(divide="ignore", invalid="ignore"):
        share = np.nanmedian(stars / stars[:, -1:, :], axis=(0, 2))
    return {"radii": list(by["radii"]), "share": share.tolist(), "correction_mag": (-2.5 * np.log10(share)).tolist()}
