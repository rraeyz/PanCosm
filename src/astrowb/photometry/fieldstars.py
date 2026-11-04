"""Every star in the field: PSF photometry for crowded fields and a search for variable stars.

PSF photometry: a circular Gaussian of the frame's FWHM is fitted to each star (photutils, BSD); stars closer
than 2.5 FWHM are fitted together, so blended neighbours share the light correctly (DAOPHOT's idea,
Stetson 1987). The local sky comes from the same annulus as aperture photometry.

Variable-star search (what Muniwin's "varfind" does): all stars detected on the first frame are measured on
every frame; magnitudes are put on a common zero point per frame (the median offset of the constant-looking
stars, iterated); each star's scatter is compared with what stars of the same brightness show. Stars well
above that magnitude-scatter relation are candidates. Index: rms / (running median rms at that magnitude).
"""

import numpy as np

from .. import timing
from ..calibration.masters import load
from ..core.citations import cites
from ..hdr import get
from .aperture import choose_apertures, despike, measure, recenter, seeing_fwhm


@cites("stetson1987")
def psf_measure(data, xy, fwhm, r_in, r_out, gain=1.0):
    """Like aperture.measure: (flux, error, sky per pixel) for each (x, y), from PSF fits."""
    from astropy.table import QTable
    from photutils.background import LocalBackground
    from photutils.psf import CircularGaussianPRF, PSFPhotometry, SourceGrouper

    data = np.asarray(data, float)
    xy = np.atleast_2d(np.asarray(xy, float))
    sky, sky_rms = _sky(data, xy, r_in, r_out)
    k = int(np.ceil(1.5 * fwhm)) * 2 + 1  # fit box: about 3 FWHM, odd
    error = np.sqrt(np.clip(data - np.median(sky), 0, None) / gain + np.median(sky_rms) ** 2)  # CCD noise per pixel
    phot = PSFPhotometry(
        CircularGaussianPRF(fwhm=fwhm),
        (k, k),
        aperture_radius=1.5 * fwhm,
        grouper=SourceGrouper(2.5 * fwhm),
        local_bkg_estimator=LocalBackground(r_in, r_out),
    )
    t = phot(data, error=error, init_params=QTable({"x_0": xy[:, 0], "y_0": xy[:, 1]}))
    flux = np.asarray(t["flux_fit"], float)
    err = np.asarray(t["flux_err"], float)
    return flux, err, np.asarray(t["local_bkg"], float)


def _sky(data, xy, r_in, r_out):
    """Sigma-clipped median and standard deviation in each star's sky annulus."""
    from astropy.stats import SigmaClip
    from photutils.aperture import ApertureStats, CircularAnnulus

    stats = ApertureStats(data, CircularAnnulus(xy, r_in=r_in, r_out=r_out), sigma_clip=SigmaClip(3.0))
    return np.asarray(stats.median, float), np.asarray(stats.std, float)


def detect_stars(data, max_stars=300, fwhm=3.0, margin=20, saturation=None):
    """(x, y) of the brightest unsaturated stars, brightest first, away from the edges."""
    from astropy.stats import sigma_clipped_stats
    from photutils.detection import DAOStarFinder

    clean = despike(data)
    _, med, std = sigma_clipped_stats(clean[::2, ::2])
    stars = DAOStarFinder(fwhm=fwhm, threshold=5 * std)(clean - med)
    if stars is None:
        return np.empty((0, 2))
    x, y = np.asarray(stars["x_centroid"]), np.asarray(stars["y_centroid"])
    peak = np.asarray(stars["peak"]) + med
    ny, nx = data.shape
    ok = (x > margin) & (x < nx - margin) & (y > margin) & (y < ny - margin)
    if saturation:
        ok &= peak < saturation
    order = np.argsort(-np.asarray(stars["flux"])[ok])[:max_stars]
    return np.column_stack([x[ok], y[ok]])[order]


def field_photometry(paths, max_stars=300, method="aperture", ctx=None):
    """Instrumental magnitudes of every star found on the first frame, on every frame.
    Returns {time (JD UTC, mid-exposure), xy (first frame), mag [frames x stars], err, radii}."""
    from ..io.inspect import saturation_level

    paths = timing.chronological([str(p) for p in paths])
    ref, h0 = load(paths[0])
    gain = get(h0, "EGAIN", "GAIN", default=1.0) or 1.0
    xy0 = detect_stars(ref, max_stars, saturation=saturation_level(h0, ref))
    if len(xy0) < 5:
        raise ValueError("fewer than 5 stars found on the first frame")
    xy0 = recenter(ref, xy0, 11)
    radii = choose_apertures(ref, xy0[: min(10, len(xy0))], gain)
    r_ap, r_in, r_out = radii["r_ap"], radii["r_in"], radii["r_out"]
    fwhm = float(radii.get("fwhm") or seeing_fwhm(ref, xy0[:10]))
    from ..calibration.stacking import align_offsets
    from ..engine.parallel import pmap

    # the shifts first (between consecutive frames, on every core, kept for the same files), then every frame on its
    # own core: 40 LCO frames x 300 stars took 60 s frame by frame
    offsets = np.asarray(align_offsets(paths, ctx))
    jobs = [(p, xy0 + off, method, fwhm, (r_ap, r_in, r_out), gain) for p, off in zip(paths, offsets, strict=True)]
    mags, errs, times = zip(*pmap(_field_frame, jobs, ctx, "photometry"), strict=True)
    return {
        "time": timing.Time(times).utc.jd.tolist(),
        "xy": xy0.tolist(),
        "mag": np.asarray(mags).tolist(),
        "err": np.asarray(errs).tolist(),
        "radii": [r_ap, r_in, r_out],
        "fwhm": fwhm,
        "method": method,
    }


def _field_frame(job):
    """One frame of field_photometry: read, re-centred from the shifted positions, measured."""
    p, pred, method, fwhm, (r_ap, r_in, r_out), gain = job
    data, h = load(p)
    xy = recenter(data, pred, 11)
    if method == "psf":
        flux, err, _ = psf_measure(data, xy, fwhm, r_in, r_out, gain)
    else:
        flux, err, _ = measure(data, xy, r_ap, r_in, r_out, gain)
    with np.errstate(divide="ignore", invalid="ignore"):
        mag = np.where(flux > 0, 25 - 2.5 * np.log10(flux), np.nan)
        return mag, np.where(flux > 0, 1.0857 * err / flux, np.nan), timing.mid_time(h)


def variability(mag, err, threshold=3.0, iterations=3):
    """Zero-point-corrected magnitudes and, per star: mean mag, rms, expected error, index, candidate.
    mag, err: [frames x stars] (NaN where a star was not measured)."""
    m = np.asarray(mag, float)
    e = np.asarray(err, float)
    good_star = np.isfinite(m).mean(axis=0) > 0.8
    weight = good_star.astype(float)
    corrected = m
    for _ in range(iterations):
        mean = np.nanmedian(m, axis=0)
        offsets = m - mean
        zp = np.array([np.nanmedian(row[(weight > 0) & np.isfinite(row)]) for row in offsets])
        corrected = m - zp[:, None]
        rms = np.nanstd(corrected, axis=0)
        expected = np.nanmedian(e, axis=0)
        weight = good_star & (rms < 2 * np.nanmedian(rms[good_star]) + 1e-9)  # leave variables out of the zero point
    mean = np.nanmedian(corrected, axis=0)
    rms = np.nanstd(corrected, axis=0)
    expected = np.nanmedian(e, axis=0)
    # typical scatter at each brightness: running median of rms over the 15 nearest stars in magnitude
    order = np.argsort(mean)
    typical = np.empty_like(rms)
    for rank, j in enumerate(order):
        near = order[max(0, rank - 7) : rank + 8]
        typical[j] = np.nanmedian(rms[near])
    spread = 1.4826 * np.nanmedian(np.abs(rms[good_star] - typical[good_star]))
    index = rms / np.maximum(typical, 1e-9)
    candidate = good_star & (rms - typical > threshold * max(spread, 1e-4)) & (rms > 2 * expected)
    return {
        "corrected": corrected.tolist(),
        "mean": mean.tolist(),
        "rms": rms.tolist(),
        "expected": expected.tolist(),
        "typical": typical.tolist(),
        "index": index.tolist(),
        "candidate": candidate.tolist(),
    }
