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
from .aperture import choose_apertures, frame_shift, measure, recenter, scintillation, seeing_fwhm
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
) -> dict:
    """Positions are 0-based (x, y) pixels in the first frame. Returns plain lists (JSON-friendly).
    auto: the three radii are chosen from the stars on the first frame (aperture.choose_apertures).
    follow_seeing: on every frame the radii are scaled by that frame's FWHM over the first frame's, so the
    aperture holds the same part of the light when the seeing changes (a "variable aperture").
    extra_xy: further stars (other targets, check stars) measured against the same comparison ensemble.
    psf: fluxes from PSF fits of each frame's FWHM (crowded fields, fieldstars.psf_measure) instead of apertures.
    aperture_m: telescope aperture (m) for the scintillation noise added to every flux error (aperture.scintillation);
    by default from APTDIA (mm) in the header. Without an aperture, the site or the target position no
    scintillation is added and "scintillation" in the result is None."""
    paths = [str(p) for p in paths]
    stars0 = np.array([target_xy, *comps_xy, *extra_xy], dtype=float)
    n_comp = len(comps_xy)
    ref, h0 = load(paths[0])
    # the clicked positions are snapped onto the stars once, within half the centroid box: with the 2.5 px limit
    # used between frames, a click 2.7 px off Qatar-1 (real LCO night) was kept and the aperture sat off the star
    # all night (light lost with the seeing, a transit moved by 20 min with radii following the seeing)
    stars0 = recenter(ref, stars0, box, max_move=box / 2)
    sky = target_coord(h0, coord)
    where = timing.location(h0)
    g = float(gain or get(h0, "EGAIN", "GAIN", default=1.0) or 1.0)
    rows = []
    prev, xy = ref, stars0
    chosen = None
    if auto:
        chosen = choose_apertures(ref, stars0[: 1 + n_comp], g)
        r_ap, r_in, r_out = chosen["r_ap"], chosen["r_in"], chosen["r_out"]
    fwhm0 = seeing_fwhm(ref, recenter(ref, stars0, box)) if follow_seeing else None
    radii, fwhms, peaks = [], [], []
    saturation = saturation_level(h0, ref)
    from concurrent.futures import ThreadPoolExecutor

    reader = ThreadPoolExecutor(1)  # the next frame is read (and decompressed) while this one is measured
    upcoming = reader.submit(load, paths[1]) if len(paths) > 1 else None
    binning = 2 if ref.size > 4e6 else 1  # large frames: the shift from 2x2-binned frames, then re-centred anyway
    for i, p in enumerate(paths):
        if ctx:
            ctx.check()
            ctx.progress(i / len(paths), "photometry")
        if i:
            data, h = upcoming.result()
            upcoming = reader.submit(load, paths[i + 1]) if i + 1 < len(paths) else None
        else:
            data, h = ref, h0
        # track frame to frame: the field can drift hundreds of pixels over a night, but little
        # between frames; positions are re-centred every frame, so errors do not accumulate
        dx, dy = (0.0, 0.0) if i == 0 else frame_shift(prev, data, binning)
        xy = recenter(data, xy + [dx, dy], box)
        prev = data
        k = 1.0
        if fwhm0:
            f = seeing_fwhm(data, xy)
            fwhms.append(f)
            k = f / fwhm0 if np.isfinite(f) and 0.2 < f / fwhm0 < 5 else 1.0  # a failed measurement keeps the radii
        radii.append([r_ap * k, r_in * k, r_out * k])
        if psf:
            from .fieldstars import psf_measure

            f = fwhms[-1] if fwhms else seeing_fwhm(data, xy[: 1 + n_comp])
            flux, err, skylev = psf_measure(data, xy, f if np.isfinite(f) else r_ap / 1.5, *radii[-1][1:], g)
        else:
            flux, err, skylev = measure(data, xy, *radii[-1], g)
        peaks.append(_peaks(data, xy, radii[-1][0]))
        try:
            t = timing.mid_time(h)
        except timing.TimeError:  # no time in the file (a screenshot, a converted picture): the frame order
            t = None
        rows.append((p, t, flux, err, skylev, xy, get(h, "EXPTIME", "EXPOSURE", default=0.0)))
    reader.shutdown(wait=False)
    if any(r[1] is None for r in rows):  # without times the light curve is against the frame number
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


def _peaks(data, xy, r_ap):
    """Brightest pixel inside each aperture (for saturation warnings)."""
    from photutils.aperture import ApertureStats, CircularAperture

    return np.atleast_1d(ApertureStats(np.asarray(data, float), CircularAperture(xy, r=r_ap)).max).tolist()


def normalise(rel, mask=None):
    """Divide by the median of the points in mask (e.g. out-of-transit), all points if None."""
    rel = np.asarray(rel, dtype=float)
    return rel / np.nanmedian(rel if mask is None else rel[mask])
