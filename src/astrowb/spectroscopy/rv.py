"""Radial velocities: continuum normalisation, cross-correlation, barycentric correction.

CCF: observed and template spectra are resampled on a common ln(lambda) grid whose step is
one velocity step, so a shift of k bins is k * v_step. The normalised (Pearson) correlation
C(k) is computed for every lag; the peak is refined with a parabola through the three highest
points. Error after Zucker (2003, MNRAS 342, 1291), maximum-likelihood form:
    sigma_v^2 = -[ N * C''/C * C^2 / (1 - C^2) ]^-1 * v_step^2
N = number of overlapping bins, C'' the second derivative (per bin^2) at the peak.

Barycentric correction (astropy, Wright & Eastman 2014 style):
    v_bary = v_obs + v_corr + v_obs * v_corr / c
"""

import numpy as np

C_KMS = 299792.458


def v_from_ln(s):
    """Velocity (km/s) of a shift s in ln(lambda). Spectra shift as lambda_obs = lambda (1 + v/c) (the optical
    convention catalogues and the barycentric correction use), so v = c (e^s - 1); c s is short by v^2 / 2c
    (17 m/s at 100 km/s, 150 m/s at 300 km/s), which also pulled every orbit's gamma down."""
    return C_KMS * np.expm1(s)


def ln_from_v(v):
    """The shift in ln(lambda) of a star moving at v (km/s)."""
    return np.log1p(np.asarray(v, float) / C_KMS)


def continuum_normalise(wave, flux, order=3, iterations=8, low=1.5, high=3.0):
    """Divide by an upper-envelope polynomial fit (absorption lines clipped low, spikes high)."""
    wave, flux = np.asarray(wave, float), np.asarray(flux, float)
    x = (wave - wave.mean()) / np.ptp(wave)
    keep = np.isfinite(flux)
    for _ in range(iterations):
        coef = np.polyfit(x[keep], flux[keep], order)
        cont = np.polyval(coef, x)
        resid = flux - cont
        sd = np.std(resid[keep])
        new = keep & (resid >= -low * sd) & (resid <= high * sd)
        if np.array_equal(new, keep) or new.sum() <= order + 1:
            break
        keep = new
    return flux / cont


def match_template(wave, t_wave, t_flux, fwhm_pixels=2.5):
    """The template smoothed to the observed spectrum's resolution when it is much finer (a solar atlas against a
    small spectrograph): sampled at the observed pixels it aliases, each pixel catching whatever sharp line edge it
    lands on (LAMOST R 1800 against the Kurucz atlas came out 60 km/s off). A Gaussian of fwhm_pixels observed
    pixels (about the resolution of a Nyquist-sampled spectrograph), as IRAF fxcor / iSpec users match templates.
    A template that is not much finer is returned as it is."""
    wave, t_wave, t_flux = (np.asarray(a, float) for a in (wave, t_wave, t_flux))
    d_obs = float(np.median(np.diff(np.log(wave))))
    ln_t = np.log(t_wave)
    d_t = float(np.median(np.diff(ln_t)))
    if not d_t < 0.25 * d_obs:
        return t_wave, t_flux
    from scipy.ndimage import gaussian_filter1d

    grid = np.arange(ln_t[0], ln_t[-1], d_t)
    smooth = gaussian_filter1d(np.interp(grid, ln_t, t_flux), fwhm_pixels * d_obs / 2.3548 / d_t, mode="nearest")
    return np.exp(grid), smooth


def chunk_error(wave, flux, t_wave, t_flux, v_min, v_max, chunks=4):
    """Empirical velocity error: the scatter of the velocities from `chunks` equal parts of the spectrum
    (std / sqrt(n)), as pipelines check the formal error order by order. None when fewer than three parts give a
    velocity. On 30 amateur spectra of AG Dra at R 500-1100 the formal CCF errors were 5-10 times too small."""
    edges = np.exp(np.linspace(np.log(wave[0]), np.log(wave[-1]), chunks + 1))
    v = []
    for a, b in zip(edges[:-1], edges[1:], strict=True):
        part = (wave >= a) & (wave <= b)
        if part.sum() < 50:
            continue
        try:
            v.append(ccf(wave[part], flux[part], t_wave, t_flux, v_min, v_max)["rv"])
        except ValueError:  # no clear peak in this part
            continue
    return float(np.std(v, ddof=1) / np.sqrt(len(v))) if len(v) >= 3 else None


def ccf(wave, flux, t_wave, t_flux, v_min=-300.0, v_max=300.0, v_step=None):
    """Return dict(v, ccf, rv, rv_err, peak). Inputs continuum-normalised (lines below 1)."""
    wave, flux, t_wave, t_flux = (np.asarray(a, float) for a in (wave, flux, t_wave, t_flux))
    if v_step is None:  # half the observed sampling
        v_step = 0.5 * C_KMS * np.median(np.diff(np.log(wave)))
    dln = v_step / C_KMS
    lo = max(np.log(wave[0]), np.log(t_wave[0]) - v_min / C_KMS)
    hi = min(np.log(wave[-1]), np.log(t_wave[-1]) - v_max / C_KMS)
    if hi - lo < 50 * dln:
        raise ValueError("observed and template spectra hardly overlap")
    grid = np.arange(lo, hi, dln)
    f = np.interp(grid, np.log(wave), flux) - 1.0
    f -= f.mean()
    lags = np.arange(int(np.floor(v_min / v_step)), int(np.ceil(v_max / v_step)) + 1)
    ln_t = np.log(t_wave)
    # independent pixels for the error formula: the grid is finer than the spectrum (half a pixel by default) and
    # its interpolated points are not data (counting them made the errors sqrt(2) too small)
    n = len(grid) * min(1.0, dln / float(np.median(np.diff(np.log(wave)))))
    c = np.empty(len(lags))
    fn = np.sqrt(np.sum(f * f))
    for i, k in enumerate(lags):
        # a star moving at v = k * v_step shows the template's line at ln(lambda) + k*dln:
        # compare observed(ln l) with template(ln l - k*dln)
        seg = np.interp(grid - k * dln, ln_t, t_flux) - 1.0
        seg = seg - seg.mean()
        c[i] = np.sum(f * seg) / (fn * np.sqrt(np.sum(seg * seg)) + 1e-30)
    j = int(np.argmax(c))
    if j in (0, len(c) - 1):
        raise ValueError("CCF peak at the edge of the velocity range: widen the range")
    y0, y1, y2 = c[j - 1], c[j], c[j + 1]
    curv = y0 - 2 * y1 + y2
    frac = 0.5 * (y0 - y2) / curv if curv != 0 else 0.0
    peak = y1 - 0.25 * (y0 - y2) * frac
    shift = (lags[j] + frac) * dln
    rv = v_from_ln(shift)
    c2 = curv  # per bin^2
    var_bins = -1.0 / (n * c2 / peak * peak**2 / (1 - peak**2)) if peak < 1 and c2 < 0 else np.nan
    return {
        "v": v_from_ln(lags * dln).tolist(),
        "ccf": c.tolist(),
        "rv": float(rv),
        "rv_err": float(np.sqrt(var_bins) * dln * C_KMS * np.exp(shift)),
        "peak": float(peak),
    }


def barycentric_correction(time, coord, location) -> float:
    """km/s to add (relativistically) to an observed velocity."""
    return float(coord.radial_velocity_correction(kind="barycentric", obstime=time, location=location).to_value("km/s"))


def to_barycentric(v_obs, v_corr):
    return v_obs + v_corr + v_obs * v_corr / C_KMS
