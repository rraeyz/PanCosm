"""Differential light curve of one target against an ensemble of comparison stars.

rel_flux = F_target / sum(F_comp);  relative error from the propagated flux errors:
    (s_rel / rel)^2 = (s_t / F_t)^2 + sum(s_c^2) / (sum F_c)^2
Times are mid-exposure; BJD_TDB when the target's sky position is known, else JD_UTC.
"""

from pathlib import Path

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord

from .. import timing
from ..calibration.masters import load
from ..hdr import get, number
from ..io.inspect import saturation_level
from .aperture import choose_apertures, frame_shift, measure, measure_cube, recenter, scintillation, seeing_fwhm
from .differential import ensemble


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
) -> dict:
    """Positions are 0-based (x, y) pixels in the first frame. Returns plain lists (JSON-friendly).
    auto: the three radii are chosen from the stars on the first frame (aperture.choose_apertures).
    follow_seeing: on every frame the radii are scaled by that frame's FWHM over the first frame's, so the
    aperture holds the same part of the light when the seeing changes (a "variable aperture").
    extra_xy: further stars (other targets, check stars) measured against the same comparison ensemble.
    psf: fluxes from PSF fits of each frame's FWHM (crowded fields, fieldstars.psf_measure) instead of apertures.
    aperture_m: telescope aperture (m) for the scintillation noise added to every flux error (aperture.scintillation);
    by default from APTDIA (mm) in the header. Without an aperture, the site or the target position no
    scintillation is added and "scintillation" in the result is None.
    ref_path: the frame the positions were marked on, when not the first in time: they are re-centred there and
    carried to the first frame by the shift between the two (as between consecutive frames).
    camera: {"read_noise": e-, "dark": e- per pixel per second}: the sky noise of every pixel from the camera's numbers
    and the sky level, as AstroImageJ (Collins et al. 2017, appendix B), instead of the scatter measured in the sky
    ring (aperture.measure).
    sky_method: how the sky ring gives the sky (aperture.sky_estimate): median, mode, mean or plane."""
    paths = [str(p) for p in paths]
    stars0 = np.array([target_xy, *comps_xy, *extra_xy], dtype=float)
    n_comp = len(comps_xy)
    ref, h0 = load(paths[0])
    # the clicked positions are snapped onto the stars once, within half the centroid box: with the 2.5 px limit
    # used between frames, a click 2.7 px off Qatar-1 (real LCO night) was kept and the aperture sat off the star
    # all night (light lost with the seeing, a transit moved by 20 min with radii following the seeing)
    if ref_path and str(ref_path) != paths[0]:
        marked = load(ref_path)[0]
        stars0 = recenter(marked, stars0, box, max_move=box / 2)
        stars0 = stars0 + frame_shift(marked, ref, 2 if ref.size > 4e6 else 1)
    stars0 = recenter(ref, stars0, box, max_move=box / 2)
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
    fwhm0 = seeing_fwhm(ref, recenter(ref, stars0, box)) if follow_seeing else None
    radii, fwhms, peaks = [], [], []
    saturation = saturation_level(h0, ref)
    from concurrent.futures import ThreadPoolExecutor

    from ..io import tpf

    src = None if psf or follow_seeing else tpf.source(paths)
    if src is not None:  # the cadences of a TESS / Kepler pixel file: measured at once, the stars do not move
        rows, peaks, radii, src_times = _pixel_file_rows(src, paths, stars0, (r_ap, r_in, r_out), g, box)
    binning = 2 if ref.size > 4e6 else 1  # large frames: the shift from 2x2-binned frames, then re-centred anyway
    from ..engine.parallel import pmap, workers

    parallel = src is None and workers() > 1 and len(paths) >= 24
    if parallel:  # every frame on its own core: the shifts first (between consecutive frames, also in parallel),
        # then each frame read, re-centred from the shifted positions and measured where it is read
        from ..calibration.stacking import align_offsets

        offsets = np.asarray(align_offsets(paths, ctx, binning))
        jobs = [
            (p, stars0 + off, stars0, (r_ap, r_in, r_out), g, box, fwhm0, psf, n_comp, paths[0], camera, sky_method)
            for p, off in zip(paths, offsets, strict=True)
        ]
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
        shift = np.zeros(2) if i == 0 else np.asarray(frame_shift(ref, data, binning))
        xy, flux, err, skylev, r, f, lost = _measure_frame(
            data,
            h,
            stars0 + shift,
            stars0,
            (r_ap, r_in, r_out),
            g,
            box,
            fwhm0,
            psf,
            n_comp,
            paths[0],
            camera=camera,
            sky_method=sky_method,
        )
        if fwhm0:
            fwhms.append(f)
        radii.append(r)
        peaks.append(_peaks(data, xy, r[0]))
        try:
            t = timing.mid_time(h)
        except timing.TimeError:  # no time in the file (a screenshot, a converted picture): the frame order
            t = None
        rows.append((p, t, flux, err, skylev, xy, get(h, "EXPTIME", "EXPOSURE", default=0.0), lost))
    reader.shutdown(wait=False)
    gone = [(Path(r[0]).name, *r[7]) for r in rows if r[7]]
    keep = [k for k, r in enumerate(rows) if not r[7]]
    if not keep:
        raise ValueError(
            "the target or a comparison star was not found on any frame: check the stars marked on the first frame"
        )
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
    flux = np.array([r[2] for r in rows])
    err = np.array([r[3] for r in rows])
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
        "rel_flux": rel.tolist(),
        "rel_flux_err": rel_err.tolist(),
        "target_flux": flux[:, 0].tolist(),
        "target_flux_err": err[:, 0].tolist(),
        "comp_flux": cf.tolist(),
        "comp_flux_err": ce.tolist(),
        "peak": peaks,  # brightest pixel in each star's aperture (target, comparisons, extra stars)
        "saturation": saturation,
        "sky": [r[4].tolist() for r in rows],
        "xy": [r[5].tolist() for r in rows],
        "coord": sky.to_string("hmsdms") if sky is not None else None,
        "radii": radii,  # aperture, inner and outer sky radius used on each frame (pixels)
        "scintillation": None if scint is None else scint.tolist(),  # relative, per frame
        "aperture_m": aperture_m,
        # frames left out, with why: {file: ["target"] / ["comparison", k] / ["aligned"]} (a dict: never taken for
        # a per-frame list by code that filters the frames)
        "lost": {x[0]: list(x[1:]) for x in gone},
    }
    if chosen:
        out["apertures"] = chosen
    if fwhms:
        out["fwhm"] = fwhms
    if len(extra_xy):
        out["extra_flux"] = flux[:, 1 + n_comp :].tolist()
        out["extra_flux_err"] = err[:, 1 + n_comp :].tolist()
    if airmass is not None:
        out["airmass"] = airmass
    return out


def _frame(job):
    """One frame of light_curve's parallel path: read, re-centred from the predicted positions, measured, checked."""
    p, pred, stars0, radii0, g, box, fwhm0, psf, n_comp, ref_path, camera, sky_method = job
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
    out = _measure_frame(
        data, h, pred, stars0, radii0, g, box, fwhm0, psf, n_comp, ref_path, partial, camera, sky_method
    )
    if out is None:  # the stars were not where the shifts put them: the whole frame, matched by its star pattern
        data, h = load(p)
        out = _measure_frame(
            data, h, pred + corner, stars0, radii0, g, box, fwhm0, psf, n_comp, ref_path, False, camera, sky_method
        )
        corner = np.zeros(2)
    xy, flux, err, skylev, radii, f, lost = out
    try:
        t = timing.mid_time(h)
    except timing.TimeError:
        t = None
    row = (p, t, flux, err, skylev, xy + corner, get(h, "EXPTIME", "EXPOSURE", default=0.0), lost)
    return row, _peaks(data, xy, radii[0]), radii, f


SNR_FOUND = 3.0  # a star whose flux is below 3 sigma of its noise is not there (empty sky, clouds)
_REF_STARS = {}  # reference frame -> its bright stars, for star-pattern matching (once per process)


def _ref_stars(ref_path):
    from ..calibration import starmatch

    if _REF_STARS.get("path") != ref_path:
        _REF_STARS.update(path=ref_path, xy=starmatch.stars(load(ref_path)[0]))
    return _REF_STARS["xy"]


def _measure_frame(
    data, h, pred, stars0, radii0, g, box, fwhm0, psf, n_comp, ref_path, partial=False, camera=None, sky_method="median"
):
    """Centre, measure and check the stars of one frame from their predicted positions (the reference frame's
    positions stars0 moved by the frame's shift). When the target or a comparison star is not found there, the frame
    is matched to the reference by its star pattern (a wrong shift, a large jump, rotation: a meridian flip) and
    measured again; a frame read in part (partial) returns None instead, to be read whole. Returns positions, fluxes,
    errors, sky, radii, FWHM and why the frame is left out: () when it is good, ("target",) when the target is not
    there, ("comparison", k) for comparison star k (1-based), ("aligned",) when the frame could not be placed."""
    from ..calibration import starmatch

    out = _measure_at(data, h, pred, radii0, g, box, fwhm0, psf, n_comp, camera, sky_method)
    lost = _lost(out, n_comp)
    if lost:
        if partial:
            return None
        try:
            m, t, _, _ = starmatch.match(_ref_stars(ref_path), starmatch.stars(data))
            again = _measure_at(
                data, h, np.asarray(stars0) @ m.T + t, radii0, g, box, fwhm0, psf, n_comp, camera, sky_method
            )
            if _rank(_lost(again, n_comp)) < _rank(lost):
                out, lost = again, _lost(again, n_comp)
        except ValueError:  # no pattern to match (clouds, an empty frame): left as it is
            pass
    return (*out[:-1], lost)


def _lost(out, n_comp):
    """Why a measured frame cannot be used, () when it can (see _measure_frame)."""
    xy, flux, err, skylev, radii, f, found = out
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


def _rank(lost):
    """Lower is better: a good frame, then one comparison star missing, then the target, then not placed."""
    return {(): 0, "comparison": 1, "target": 2, "aligned": 3}[lost[0] if lost else ()]


def _measure_at(data, h, pred, radii0, g, box, fwhm0, psf, n_comp, camera=None, sky_method="median"):
    """Centroids from the predicted positions, then the fluxes (apertures or PSF); found: centroid near the
    prediction."""
    r_ap, r_in, r_out = radii0
    xy, found = recenter(data, pred, box, found=True)
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
        cam = None
        if camera:  # dark current over this frame's exposure
            exptime = get(h, "EXPTIME", "EXPOSURE", default=0.0) or 0.0
            cam = (float(camera.get("read_noise", 0.0)), float(camera.get("dark", 0.0)) * exptime)
        flux, err, skylev = measure(data, xy, *radii, g, h.get("PIXNOISE"), cam, sky_method)
    return xy, flux, err, skylev, radii, f, found


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
    return rows, peak.tolist(), [list(radii)] * len(paths), (bjd, utc)


def _peaks(data, xy, r_ap):
    """Brightest pixel inside each aperture (for saturation warnings)."""
    from photutils.aperture import ApertureStats, CircularAperture

    return np.atleast_1d(ApertureStats(np.asarray(data, float), CircularAperture(xy, r=r_ap)).max).tolist()


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
