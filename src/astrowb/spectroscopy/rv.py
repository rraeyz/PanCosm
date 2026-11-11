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


def continuum_normalise(wave, flux, order=3, iterations=8, low=1.5, high=3.0, piece=8000):
    """Divide by an upper-envelope polynomial fit (absorption lines clipped low, spikes high). A spectrum of more than
    `piece` pixels (a merged echelle spectrum) is fitted in pieces of about that many: one cubic over 1500 A of a
    real HARPS spectrum left the merged orders' continuum in and its velocity came out 5.6 km/s off. The pieces
    overlap by half and are blended (fitted one after the other they jumped by up to 0.45 where they met, on 3 of 7
    HARPS spectra against IRAF continuum's spline). Exact zeros are no data (the HARPS CCD gap at 5300 A)."""
    wave, flux = np.asarray(wave, float), np.asarray(flux, float)
    if len(wave) <= piece:
        return flux / _continuum(wave, flux, order, iterations, low, high)
    starts = np.unique(np.r_[np.arange(0, len(wave) - piece, piece // 2), len(wave) - piece])
    total, weight = np.zeros(len(wave)), np.zeros(len(wave))
    ramp = 1e-3 + 1 - np.abs(np.linspace(-1, 1, piece))  # most weight in the middle of each piece
    for a in starts:
        cont = _continuum(wave[a : a + piece], flux[a : a + piece], order, iterations, low, high)
        ok = np.isfinite(cont)
        total[a : a + piece][ok] += ramp[ok] * cont[ok]
        weight[a : a + piece][ok] += ramp[ok]
    with np.errstate(invalid="ignore", divide="ignore"):
        return flux / (total / weight)


def _continuum(wave, flux, order, iterations, low, high):
    """The upper-envelope polynomial of continuum_normalise (NaN where it has too few points to fit)."""
    x = (wave - wave.mean()) / np.ptp(wave)
    keep = np.isfinite(flux) & (flux != 0)
    if keep.sum() <= order + 1:
        return np.full(len(wave), np.nan)
    v = np.vander(x, order + 1)  # x within +-0.5: normal equations well conditioned (polyfit took 3/4 of the time)
    f0 = np.where(keep, flux, 0.0)
    for _ in range(iterations):
        vk = v * keep[:, None]
        cont = v @ np.linalg.solve(vk.T @ v, vk.T @ f0)
        resid = flux - cont
        sd = np.std(resid[keep])
        new = keep & (resid >= -low * sd) & (resid <= high * sd)
        if np.array_equal(new, keep) or new.sum() <= order + 1:
            break
        keep = new
    return cont


def rotate(wave, flux, vsini):
    """A continuum-normalised template's lines broadened by rotation (Gray's profile, limb darkening 0.6), as TODCOR
    and fxcor users match a sharp-lined template to a fast rotator (TZ For's F giant, v sin i 46 km/s: with the sharp
    template its HARPS velocities came out 40-80 km/s off Gallenne et al. 2016, broadened 0.3-0.7 km/s). Returns the
    template on a log-uniform grid; vsini 0 returns it unchanged."""
    if not vsini:
        return wave, flux
    from .atmosphere import rotation_kernel

    ln = np.log(np.asarray(wave, float))
    d = float(np.median(np.diff(ln)))
    grid = np.arange(ln[0], ln[-1], d)
    f = np.interp(grid, ln, np.asarray(flux, float)) - 1.0
    return np.exp(grid), np.convolve(f, rotation_kernel(float(vsini), C_KMS * d), mode="same") + 1.0


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


def mask_emission(flux, t_flux, k=3.0):
    """Emission lines set to the continuum before correlating with an absorption-line template (IRAF fxcor users
    mask them by hand): they correlate negatively and pull the velocity (an AG Dra spectrum at R 700: -304 instead
    of -158 km/s). Inputs continuum-normalised. Left as they are when the template shows emission itself. Returns
    the flux and the number of pixels masked."""
    flux, t_flux = np.asarray(flux, float), np.asarray(t_flux, float)

    def noise(y):
        return 1.4826 * np.nanmedian(np.abs(np.diff(y))) / np.sqrt(2)

    if np.nanmean(t_flux - 1 > k * noise(t_flux) + 0.02) > 0.001:  # the template has emission lines too
        return flux, 0
    high = (flux - 1) > k * noise(flux)
    return np.where(high, 1.0, flux), int(high.sum())


def chunk_error(wave, flux, t_wave, t_flux, v_min, v_max, chunks=4):
    """Empirical velocity error by the jackknife over wavelength chunks: the velocity of the whole spectrum with one
    chunk left out (set to the continuum) at a time; sigma^2 = (n-1)/n * sum (v_i - mean)^2. A part that disagrees
    counts as much as it moves the whole result. Pipelines check the formal error in the same spirit, order by order.
    On 30 amateur spectra of AG Dra at R 500-1100 the formal errors were 5-10 times too small; the plain scatter of
    the chunks' own velocities overstated LAMOST errors tenfold (a telluric or arm-join chunk is far off on its own
    but hardly moves the whole). None when fewer than three chunks give a velocity."""
    edges = np.exp(np.linspace(np.log(wave[0]), np.log(wave[-1]), chunks + 1))
    v = []
    for a, b in zip(edges[:-1], edges[1:], strict=True):
        without = np.where((wave >= a) & (wave <= b), 1.0, flux)
        try:
            v.append(ccf(wave, without, t_wave, t_flux, v_min, v_max)["rv"])
        except ValueError:  # no clear peak without this part
            continue
    if len(v) < 3:
        return None
    v = np.asarray(v)
    return float(np.sqrt((len(v) - 1) / len(v) * np.sum((v - v.mean()) ** 2)))


def shifted(lo, dln, m, lags, ln_t, t):
    """The template t (sampled at ln_t) at ln = lo + (i - k) dln for i < m and every lag k, interpolated once (not
    once per lag): (t_ext, start), the lag's values being t_ext[start + j], j < m, for each start."""
    lags = np.asarray(lags)
    return np.interp(lo + np.arange(-lags.max(), m - lags.min()) * dln, ln_t, t), lags.max() - lags


def lag_dot(f, t_ext, start):
    """For every lag: sum(f * (seg - mean(seg))) and |seg - mean(seg)|, seg = t_ext[start + j] (f has zero mean)."""
    m = len(f)
    dot = np.correlate(t_ext, f, mode="valid")[start]  # sum f * (seg - mean) = sum f * seg, f having zero mean
    c1 = np.concatenate([[0.0], np.cumsum(t_ext)])
    c2 = np.concatenate([[0.0], np.cumsum(t_ext * t_ext)])
    seg_sum, seg_sq = c1[start + m] - c1[start], c2[start + m] - c2[start]
    return dot, np.sqrt(np.maximum(seg_sq - seg_sum**2 / m, 0.0))


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
    fn = np.sqrt(np.sum(f * f))
    # a star moving at v = k * v_step shows the template's line at ln(lambda) + k*dln: observed(ln l) is compared with
    # template(ln l - k*dln), a slice of the template put once on the grid extended by the lags (interpolating it
    # again for every lag took 35 of 37 s for two HARPS spectra; IRAF fxcor measures seven in 1.4 s)
    dot, norm = lag_dot(f, *shifted(lo, dln, len(grid), lags, ln_t, t_flux - 1.0))
    c = dot / (fn * norm + 1e-30)
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
    from ..core.units import velocity_correction

    return float(velocity_correction(time, coord, location))


def to_barycentric(v_obs, v_corr):
    return v_obs + v_corr + v_obs * v_corr / C_KMS
