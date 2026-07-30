"""Working on a 1-D spectrum (what IRAF splot, BASS, ISIS and RSpec offer).

- Line measurement in a window: continuum through the window edges, equivalent width by direct
  integration (error: pixel noise propagated plus the continuum placement, the two terms of Vollmann &
  Eversberg 2006, AN 327, 862, evaluated per pixel instead of their closed form), flux-weighted centre,
  integrated line flux, and a Gaussian or Voigt fit (centre, FWHM, depth, EW) with errors.
- Be-star emission: V/R of the violet and red emission peaks, (I_V - 1) / (I_R - 1) on the
  normalised spectrum, with the peak velocities.
- Arithmetic between spectra (the second resampled onto the first's wavelengths), smoothing
  (boxcar, Gaussian, median), resampling to an even step, continuum through hand-picked points.
- Instrument response: observed / reference spectrum of a star of known energy distribution, with
  stellar lines and telluric bands masked, smoothed by a least-squares spline; dividing by it gives
  relative flux (as ISIS and BASS do).
- Export for the BeSS / ARAS databases: 1-D FITS image, linear wavelength (Angstrom), BeSS keywords.
"""

import numpy as np

C_KMS = 299792.458

# Air wavelengths (Angstrom), NIST; the ones amateur and professional spectra are read with.
LINES = {
    "Hα": 6562.80,
    "Hβ": 4861.33,
    "Hγ": 4340.47,
    "Hδ": 4101.74,
    "Hε": 3970.07,
    "He I 4026": 4026.19,
    "He I 4471": 4471.48,
    "He I 4922": 4921.93,
    "He I 5876": 5875.62,
    "He I 6678": 6678.15,
    "He I 7065": 7065.19,
    "He II 4686": 4685.70,
    "He II 5412": 5411.52,
    "Ca II K": 3933.66,
    "Ca II H": 3968.47,
    "Ca II 8498": 8498.02,
    "Ca II 8542": 8542.09,
    "Ca II 8662": 8662.14,
    "Na I D2": 5889.95,
    "Na I D1": 5895.92,
    "Mg I b1": 5183.60,
    "Mg I b2": 5172.68,
    "Mg I b4": 5167.32,
    "Mg II 4481": 4481.13,
    "Si II 6347": 6347.11,
    "Si II 6371": 6371.37,
    "Fe II 5169": 5169.03,
    "Fe I 5270": 5269.54,
    "O I 7774": 7774.17,
    "C III 4647": 4647.42,
    "N III 4641": 4640.64,
    "C IV 5801": 5801.33,
    "C IV 5812": 5811.98,
    "[O III] 4959": 4958.91,
    "[O III] 5007": 5006.84,
    "[N II] 6548": 6548.05,
    "[N II] 6583": 6583.45,
    "[S II] 6716": 6716.44,
    "[S II] 6731": 6730.82,
    "[O I] 6300": 6300.30,
}

# Regions left out of a response fit: Balmer and other strong stellar lines (+-) and telluric bands.
_MASK_LINES = (6562.8, 4861.3, 4340.5, 4101.7, 3970.1, 3889.1, 3835.4, 3933.7, 3968.5, 5890.0, 8542.1, 8662.1)
_TELLURIC = ((6270, 6330), (6860, 6960), (7160, 7340), (7590, 7700), (8130, 8350), (8950, 9800))


def _window(wave, flux, lo, hi):
    wave, flux = np.asarray(wave, float), np.asarray(flux, float)
    sel = (wave >= min(lo, hi)) & (wave <= max(lo, hi)) & np.isfinite(flux)
    if sel.sum() < 7:
        raise ValueError("too few points in the window")
    return wave[sel], flux[sel]


def edge_continuum(w, f, edge=0.1):  # edge fraction: keep in step with measure_line's k
    """Straight continuum through the medians of the outer `edge` fraction of the window at each end;
    also the signal-to-noise of those continuum points."""
    k = max(3, int(edge * w.size))
    xl, yl, xr, yr = np.mean(w[:k]), np.median(f[:k]), np.mean(w[-k:]), np.median(f[-k:])
    cont = yl + (yr - yl) * (w - xl) / (xr - xl)
    edges = np.r_[f[:k] / cont[:k], f[-k:] / cont[-k:]]
    snr = 1 / np.std(edges, ddof=1) if np.std(edges) > 0 else np.inf
    return cont, float(snr)


def _profile(x, centre, sigma, gamma, kind):
    from scipy.special import voigt_profile

    if kind == "gauss":
        return np.exp(-0.5 * ((x - centre) / sigma) ** 2)
    return voigt_profile(x - centre, sigma, gamma) / voigt_profile(0.0, sigma, gamma)


def _fwhm(sigma, gamma, kind):
    fg = 2 * np.sqrt(2 * np.log(2)) * sigma
    if kind == "gauss":
        return fg
    fl = 2 * gamma
    return 0.5346 * fl + np.sqrt(0.2166 * fl * fl + fg * fg)  # Olivero & Longbothum 1977


def measure_line(wave, flux, lo, hi, profile="gauss"):
    """Measure the line between lo and hi (Angstrom). EW > 0 for absorption, < 0 for emission."""
    from scipy.optimize import least_squares
    from scipy.special import voigt_profile

    w, f = _window(wave, flux, lo, hi)
    cont, snr = edge_continuum(w, f)
    r = f / cont
    dw = np.gradient(w)
    ew = float(np.sum((1 - r) * dw))
    depth = 1 - r
    centroid = float(np.sum(depth * w) / np.sum(depth)) if abs(depth.sum()) > 0 else float(w[np.argmax(abs(depth))])
    k = max(3, int(0.1 * w.size))
    ew_err = 0.0
    if np.isfinite(snr):  # noise of each pixel + error of the continuum level (mean of 2k edge points)
        ew_err = float(np.hypot(np.sqrt(np.sum((dw * r / snr) ** 2)), (np.ptp(w) - ew) / (snr * np.sqrt(2 * k))))
    i = int(np.argmax(np.abs(depth)))
    a0, c0 = depth[i], w[i]
    half = np.abs(depth) > abs(a0) / 2
    s0 = max(np.ptp(w[half]) / 2.355 if half.sum() > 1 else 2 * np.median(dw), np.median(dw))

    def model(p):
        return 1 - p[1] * _profile(w, p[0], p[2], p[3] if profile == "voigt" else 0.0, profile)

    p0 = [c0, a0, s0] + ([s0 / 2] if profile == "voigt" else [])
    lo_b = [w[0], -np.inf, np.median(dw) / 10] + ([0.0] if profile == "voigt" else [])
    hi_b = [w[-1], np.inf, np.ptp(w)] + ([np.ptp(w)] if profile == "voigt" else [])
    res = least_squares(lambda p: model(p) - r, p0, bounds=(lo_b, hi_b), x_scale="jac")
    p = res.x
    dof = max(1, r.size - len(p))
    cov = np.linalg.pinv(res.jac.T @ res.jac) * np.sum(res.fun**2) / dof
    e = np.sqrt(np.abs(np.diag(cov)))
    sigma, gamma = p[2], (p[3] if profile == "voigt" else 0.0)
    area = sigma * np.sqrt(2 * np.pi) if profile == "gauss" else 1 / voigt_profile(0.0, sigma, gamma)
    return {
        "lo": float(w[0]),
        "hi": float(w[-1]),
        "ew": ew,
        "ew_err": ew_err,
        "centroid": centroid,
        "line_flux": float(np.sum((f - cont) * dw)),
        "snr": snr,
        "profile": profile,
        "centre": float(p[0]),
        "centre_err": float(e[0]),
        "depth": float(p[1]),
        "depth_err": float(e[1]),
        "fwhm": float(_fwhm(sigma, gamma, profile)),
        "fwhm_err": float(2.355 * e[2]),
        "ew_fit": float(p[1] * area),
        "continuum": cont.tolist(),
        "model": (cont * model(p)).tolist(),
        "wave": w.tolist(),
    }


def v_over_r(wave, flux, centre, half_width):
    """V/R of a double-peaked emission line on a normalised spectrum: (I_V - 1) / (I_R - 1), and the
    peak velocities (km/s) relative to centre."""
    w, f = np.asarray(wave, float), np.asarray(flux, float)
    blue = (w >= centre - half_width) & (w < centre)
    red = (w > centre) & (w <= centre + half_width)
    if blue.sum() < 3 or red.sum() < 3:
        raise ValueError("too few points on one side of the line")
    iv, ir = int(np.argmax(np.where(blue, f, -np.inf))), int(np.argmax(np.where(red, f, -np.inf)))
    if f[ir] <= 1:
        raise ValueError("no red emission peak above the continuum")
    return {
        "v_over_r": float((f[iv] - 1) / (f[ir] - 1)),
        "v_peak": float(f[iv]),
        "r_peak": float(f[ir]),
        "v_velocity": float((w[iv] - centre) / centre * C_KMS),
        "r_velocity": float((w[ir] - centre) / centre * C_KMS),
    }


def resample_onto(wave, wave_b, flux_b):
    """flux_b on the wavelengths `wave` (NaN outside its range)."""
    return np.interp(wave, wave_b, flux_b, left=np.nan, right=np.nan)


def arithmetic(wave_a, flux_a, wave_b, flux_b, op):
    """a op b with b resampled onto a's wavelengths; op is '+', '-', '*' or '/'. b may be a number."""
    a = np.asarray(flux_a, float)
    b = float(flux_b) if np.isscalar(flux_b) else resample_onto(np.asarray(wave_a, float), wave_b, flux_b)
    with np.errstate(divide="ignore", invalid="ignore"):
        return {"+": a + b, "-": a - b, "*": a * b, "/": a / b}[op]


def smooth(flux, kind="gauss", width=3.0):
    """Boxcar (width pixels), Gaussian (FWHM pixels) or median (width pixels) smoothing."""
    from scipy import ndimage

    f = np.asarray(flux, float)
    if kind == "boxcar":
        return ndimage.uniform_filter1d(f, max(1, int(round(width))), mode="nearest")
    if kind == "median":
        return ndimage.median_filter(f, max(1, int(round(width)) | 1), mode="nearest")
    return ndimage.gaussian_filter1d(f, width / 2.3548, mode="nearest")


def resample(wave, flux, step):
    """Even wavelength grid with the given step (Angstrom), linear interpolation."""
    wave = np.asarray(wave, float)
    new = np.arange(wave.min(), wave.max() + step / 2, step)
    return new, np.interp(new, wave, flux)


def continuum_from_points(wave, flux, points, half=2):
    """Continuum through hand-picked wavelengths: each point takes the median flux of +-half pixels;
    a cubic spline through four or more points, otherwise straight lines."""
    from scipy.interpolate import CubicSpline

    wave, flux = np.asarray(wave, float), np.asarray(flux, float)
    pts = sorted(set(float(p) for p in points))
    if len(pts) < 2:
        raise ValueError("pick at least two continuum points")
    ys = []
    for p in pts:
        i = int(np.argmin(np.abs(wave - p)))
        ys.append(np.median(flux[max(0, i - half) : i + half + 1]))
    if len(pts) >= 4:
        return CubicSpline(pts, ys, bc_type="natural", extrapolate=True)(wave)
    return np.interp(wave, pts, ys)


def response(obs_wave, obs_flux, ref_wave, ref_flux, knot_spacing=150.0, line_half_width=40.0):
    """Instrument response on obs_wave: observed / reference, stellar lines (+-line_half_width) and
    telluric bands masked, least-squares cubic spline with knots every knot_spacing Angstrom,
    scaled to 1 at its median."""
    from scipy.interpolate import LSQUnivariateSpline

    w = np.asarray(obs_wave, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.asarray(obs_flux, float) / resample_onto(w, ref_wave, ref_flux)
    ok = np.isfinite(ratio) & (ratio > 0)
    for c in _MASK_LINES:
        ok &= np.abs(w - c) > line_half_width
    for a, b in _TELLURIC:
        ok &= (w < a) | (w > b)
    x, y = w[ok], ratio[ok]
    if x.size < 10:
        raise ValueError("the reference spectrum does not cover the observed one")
    knots = np.arange(x[0] + knot_spacing, x[-1] - knot_spacing / 2, knot_spacing)
    knots = knots[[np.sum((x > k - knot_spacing) & (x < k)) > 3 for k in knots]] if knots.size else knots
    spline = LSQUnivariateSpline(x, y, knots, k=3)
    resp = spline(w)
    return resp / np.median(resp[ok])


def bess_header(meta):
    """BeSS keywords from a dict (missing ones get neutral values): object, observer, date_obs,
    exptime, site, instrument, latitude, longitude, elevation, vhel (km/s applied, 0 if none),
    telluric (0/1 corrected), cosmic (0/1 removed)."""
    from astropy.io import fits

    h = fits.Header()
    h["OBJNAME"] = (str(meta.get("object", "")), "object name (Simbad)")
    h["OBSERVER"] = (str(meta.get("observer", "")), "observer")
    h["DATE-OBS"] = (str(meta.get("date_obs", "")), "start of exposure, UTC")
    h["EXPTIME"] = (float(meta.get("exptime", 0.0)), "exposure time [s]")
    h["BSS_INST"] = (str(meta.get("instrument", "")), "telescope + spectrograph + camera")
    h["BSS_SITE"] = (str(meta.get("site", "")), "observing site")
    h["BSS_LAT"] = (float(meta.get("latitude", 0.0)), "site latitude [deg]")
    h["BSS_LONG"] = (float(meta.get("longitude", 0.0)), "site longitude [deg]")
    h["BSS_ELEV"] = (float(meta.get("elevation", 0.0)), "site elevation [m]")
    h["BSS_VHEL"] = (float(meta.get("vhel", 0.0)), "heliocentric correction applied [km/s]")
    h["BSS_TELL"] = (int(bool(meta.get("telluric", 0))), "telluric lines removed (1) or not (0)")
    h["BSS_COSM"] = (int(bool(meta.get("cosmic", 0))), "cosmic rays removed (1) or not (0)")
    return h


def write_bess(path, wave, flux, meta, step=None):
    """1-D FITS image on an even wavelength grid (the step of the data unless given), Angstrom."""
    from astropy.io import fits

    wave = np.asarray(wave, float)
    step = step or float(np.median(np.diff(wave)))
    grid, f = resample(wave, flux, step)
    h = bess_header(meta)
    hdu = fits.PrimaryHDU(np.asarray(f, np.float32), header=h)
    hdu.header["CRPIX1"] = 1.0
    hdu.header["CRVAL1"] = (float(grid[0]), "wavelength of the first pixel [Angstrom]")
    hdu.header["CDELT1"] = (step, "Angstrom per pixel")
    hdu.header["CTYPE1"] = "Wavelength"
    hdu.header["CUNIT1"] = "Angstrom"
    hdu.writeto(path, overwrite=True, output_verify="silentfix")
    return str(path)
