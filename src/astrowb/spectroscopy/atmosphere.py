"""Stellar atmospheric parameters (Teff, log g, [Fe/H]) with v sin i and radial velocity, by fitting a grid of
synthetic spectra to an observed spectrum (the "synthetic spectrum fitting" approach of iSpec / SME, done here on a
precomputed grid instead of computing spectra on the fly).

Model of the observed spectrum:
    F_obs(lambda) = P_k(lambda) * [S(Teff, log g, [Fe/H]) * G_rot(v sin i) * G_inst(R)](lambda / (1 + v_r / c))
- S: the grid spectrum, interpolated linearly between the 8 surrounding grid points;
- G_rot: rotational broadening with linear limb darkening eps = 0.6 (Gray 2005, The Observation and Analysis of
  Stellar Photospheres, eq. 18.14);
- G_inst: Gaussian of FWHM c / R (the spectrograph's resolution, given by the user);
- P_k: a polynomial (degree 2) in each wavelength chunk of ~100 A, solved linearly at every step, so the spectrum
  needs neither flux calibration nor normalisation (the instrument response is absorbed);
- grid wavelengths are in vacuum and are converted to air (Morton 2000, ApJS 130, 403; the IAU standard) unless
  the observed spectrum is in vacuum.
Fit: radial velocity from a scan with a mid-grid model, then the best grid point, then Levenberg-Marquardt on the five
parameters. Errors: the fit covariance scaled by the reduced chi^2 (statistical only; the grid's own systematic
errors are found by fitting benchmark stars of known parameters).

Grid: the PHOENIX-ACES library (Husser et al. 2013, A&A 553, A6), downloaded on first use point by point and kept
as 3000-10000 A at R = 200 000 (about 1 MB per point), or any folder of FITS files in the same layout: the flux as
the primary image, its vacuum wavelengths (Angstrom) as an image extension WAVE or as LOGW0 + DLOGW * index in
ln(lambda), and TEFF, LOGG, FEH keywords.

Accuracy and the Sun. Synthetic spectra do not reproduce real stars line for line: at the Sun's own parameters
PHOENIX differs from the solar flux atlas by more than 2 % in ~40 % of the pixels, and a fit of the whole solar
spectrum misses the Sun by up to -250 K, -0.5 dex in log g and -0.4 dex in [Fe/H] (measured). So, as in iSpec,
only the wavelengths where the model reproduces the Sun are used (the mask is made at the user's resolution and
wavelength range from the Sun itself), and the result is given relative to the Sun fitted in exactly the same way
(differential analysis): star - (Sun fitted - Sun known). The Sun is the Kurucz (2005) solar flux atlas, or better,
a solar spectrum taken with the same spectrograph (twilight sky, the Moon, an asteroid), which also removes the
instrument's own systematics. This is most reliable for FGK stars not far from the Sun; for stars far from it the
result is flagged.
"""

from pathlib import Path

import numpy as np

from ..core.units import vac_to_air

C_KMS = 299792.458
PHOENIX = "https://phoenix.astro.physik.uni-goettingen.de/data/HiResFITS/"
STORE_RANGE = (3000.0, 10000.0)
STORE_R = 200_000  # samples per unit ln(lambda): 1.5 km/s
TELLURIC = ((6860, 6960), (7590, 7700), (8100, 8400), (8900, 9900))  # as templates.TELLURIC


# --- the grid -----------------------------------------------------------------------------------------------------
def phoenix_axes():
    teff = np.r_[np.arange(2300, 7000, 100), np.arange(7000, 12001, 200)]
    logg = np.arange(0.0, 6.01, 0.5)
    feh = np.array([-4.0, -3.0, -2.0, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0])
    return teff, logg, feh


def phoenix_url(teff, logg, feh):
    z = "-0.0" if feh == 0 else f"{feh:+.1f}"
    name = f"lte{int(teff):05d}-{logg:.2f}{z}.PHOENIX-ACES-AGSS-COND-2011-HiRes.fits"
    return f"{PHOENIX}PHOENIX-ACES-AGSS-COND-2011/Z{z}/{name}"


def _rebin(w_in, f_in, w_out):
    """Flux-conserving resampling: the cumulative integral interpolated at the output bin edges."""
    cum = np.concatenate([[0.0], np.cumsum(0.5 * (f_in[1:] + f_in[:-1]) * np.diff(w_in))])
    edges = np.concatenate([[w_out[0]], 0.5 * (w_out[1:] + w_out[:-1]), [w_out[-1]]])
    return np.diff(np.interp(edges, w_in, cum)) / np.diff(edges)


def store_wave():
    lo, hi = STORE_RANGE
    return np.exp(np.arange(np.log(lo), np.log(hi), 1 / STORE_R))


def _fetch(url, tries=4):
    """The bytes at url; retried, the archives drop connections now and then."""
    import time
    import urllib.request

    for k in range(tries):
        try:
            return urllib.request.urlopen(url, timeout=120).read()
        except OSError as e:
            if k == tries - 1 or getattr(e, "code", None) == 404:  # a file that is not there: no retry
                raise
            time.sleep(2 * (k + 1))


def download_phoenix(nodes, folder, fetch=None, progress=None):
    """Grid points [(teff, logg, feh)] into folder (kept: those already there). Returns the paths of the points
    that exist: the PHOENIX grid has holes (no model computed there), which are skipped and remembered."""
    import io

    from astropy.io import fits

    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    fetch = fetch or _fetch
    wave_file = folder / "phoenix_wave.npy"
    paths, wave = [], None
    for n, (t, g, z) in enumerate(nodes):
        path = folder / f"phoenix_{int(t):05d}_{g:.2f}_{z:+.1f}.fits"
        hole = path.with_suffix(".missing")
        if path.exists():
            paths.append(path)
            continue
        if hole.exists():
            continue
        if progress:
            progress(n / max(1, len(nodes)), f"PHOENIX {int(t)} {g:.1f} {z:+.1f}")
        if wave is None:
            if not wave_file.exists():
                with fits.open(io.BytesIO(fetch(PHOENIX + "WAVE_PHOENIX-ACES-AGSS-COND-2011.fits"))) as h:
                    np.save(wave_file, np.asarray(h[0].data, float))
            wave = np.load(wave_file)
        try:
            raw = fetch(phoenix_url(t, g, z))
        except OSError as e:
            if getattr(e, "code", None) != 404:
                raise
            hole.touch()
            continue
        with fits.open(io.BytesIO(raw)) as h:
            flux = np.asarray(h[0].data, float)
        out = store_wave()
        sel = (wave > out[0] - 5) & (wave < out[-1] + 5)
        hdr = fits.Header({"TEFF": float(t), "LOGG": float(g), "FEH": float(z), "SOURCE": "PHOENIX-ACES 2011"})
        hdr["LOGW0"] = (float(np.log(out[0])), "ln(vacuum wavelength / A) of the first sample")
        hdr["DLOGW"] = (1 / STORE_R, "step in ln(wavelength)")
        fits.PrimaryHDU(_rebin(wave[sel], flux[sel], out).astype(np.float32), hdr).writeto(path, overwrite=True)
        paths.append(path)
    return paths


def _count_missing(spectra, axes, i, v):
    """How many points of the full box with axis i = v are missing."""
    others = [a for k, a in enumerate(axes) if k != i]
    n = 0
    for a in others[0]:
        for b in others[1]:
            key = [a, b]
            key.insert(i, v)
            n += tuple(float(x) for x in key) not in spectra
    return n


class Grid:
    """Synthetic spectra on a regular (Teff, log g, [Fe/H]) grid, on one ln(lambda) wavelength scale (vacuum)."""

    def __init__(self, spectra, wave):
        """spectra: {(teff, logg, feh): flux}. Interpolation needs every corner, so points outside the largest
        complete (Teff x log g x [Fe/H]) box are dropped: the axis value missing most combinations goes first."""
        self.wave = wave
        spectra = dict(spectra)
        while True:
            keys = np.array(list(spectra))
            axes = [np.unique(keys[:, i]) for i in range(3)]
            missing = [[_count_missing(spectra, axes, i, v) for v in axes[i]] for i in range(3)]
            present = [[sum(k[i] == v for k in spectra) for v in axes[i]] for i in range(3)]
            worst = max((m, -present[i][j], i, j) for i in range(3) for j, m in enumerate(missing[i]))
            if worst[0] == 0:
                break
            _, _, i, j = worst
            spectra = {k: s for k, s in spectra.items() if k[i] != axes[i][j]}
            if not spectra:
                raise ValueError("the grid has no complete box of points")
        self.spectra, self.axes = spectra, axes

    @classmethod
    def load(cls, paths, wmin, wmax):
        from astropy.io import fits

        spectra, wave = {}, None
        for p in paths:
            with fits.open(p) as h:
                hd = h[0].header
                if "WAVE" in h:
                    w = np.asarray(h["WAVE"].data, float)
                else:  # evenly spaced in ln(lambda)
                    w = np.exp(hd["LOGW0"] + hd["DLOGW"] * np.arange(hd["NAXIS1"]))
                sel = (w >= wmin) & (w <= wmax)
                if wave is None:
                    wave = w[sel]
                    flux = np.asarray(h[0].data, float)[sel]
                else:  # another sampling: brought to the first file's
                    flux = np.interp(wave, w, np.asarray(h[0].data, float))
                spectra[(float(hd["TEFF"]), float(hd["LOGG"]), float(hd["FEH"]))] = flux
        if not spectra:
            raise ValueError("no grid spectra")
        return cls(spectra, wave)

    def bounds(self):
        return [a[0] for a in self.axes], [a[-1] for a in self.axes]

    def spectrum(self, teff, logg, feh):
        """Interpolated spectrum: linear in Teff and log g; quadratic (3-point Lagrange) in [Fe/H], whose line
        depths grow non-linearly with metallicity (linear interpolation over the 0.5 dex steps biased [Fe/H] by
        up to 0.05 dex in tests/test_atmosphere.py; quadratic, 0.01 dex). All the points used must exist."""
        sel, wts = [], []
        for k, (ax, v) in enumerate(zip(self.axes, (teff, logg, feh), strict=True)):
            if len(ax) == 1:
                sel.append([0])
                wts.append([1.0])
            elif k == 2 and len(ax) >= 3:
                i = int(np.clip(np.argmin(np.abs(ax - v)), 1, len(ax) - 2))
                x = ax[i - 1 : i + 2]
                sel.append([i - 1, i, i + 1])
                wts.append([np.prod([(v - x[m]) / (x[j] - x[m]) for m in range(3) if m != j]) for j in range(3)])
            else:
                i = int(np.clip(np.searchsorted(ax, v) - 1, 0, len(ax) - 2))
                f = float(np.clip((v - ax[i]) / (ax[i + 1] - ax[i]), 0, 1))
                sel.append([i, i + 1])
                wts.append([1 - f, f])
        out = 0.0
        for i, wi in zip(sel[0], wts[0], strict=True):
            for j, wj in zip(sel[1], wts[1], strict=True):
                for k, wk in zip(sel[2], wts[2], strict=True):
                    w = wi * wj * wk
                    if w != 0:
                        out = (
                            out
                            + w * self.spectra[(float(self.axes[0][i]), float(self.axes[1][j]), float(self.axes[2][k]))]
                        )
        return out


# --- the model ------------------------------------------------------------------------------------------------------
def rotation_kernel(vsini, dv, eps=0.6, over=25):
    """Gray (2005) rotational profile on a velocity step dv (km/s), averaged over each pixel (not sampled at its
    centre, which makes the profile and its derivative jump when it is only a few pixels wide); sums to 1."""
    if vsini < 0.05 * dv:
        return np.array([1.0])
    n = int(np.ceil(vsini / dv + 0.5))
    u = -(n + 0.5) + (np.arange((2 * n + 1) * over) + 0.5) / over  # sub-pixel centres, in pixels
    x = u * dv / vsini
    inside = np.abs(x) < 1
    prof = np.zeros_like(x)
    prof[inside] = 2 * (1 - eps) * np.sqrt(1 - x[inside] ** 2) + 0.5 * np.pi * eps * (1 - x[inside] ** 2)
    k = prof.reshape(2 * n + 1, over).mean(axis=1)
    return k / k.sum()


def gauss_kernel(fwhm, dv):
    s = fwhm / 2.3548 / dv
    if s < 0.3:
        return np.array([1.0])
    x = np.arange(-int(np.ceil(5 * s)), int(np.ceil(5 * s)) + 1)
    k = np.exp(-0.5 * (x / s) ** 2)
    return k / k.sum()


class Fitter:
    """The observed spectrum, its chunks and mask, and the model of it for given parameters."""

    def __init__(self, wave, flux, err, grid, resolution, air=True, chunk=100.0, degree=2, mask=()):
        from scipy.signal import fftconvolve

        self._conv = fftconvolve
        wave, flux = np.asarray(wave, float), np.asarray(flux, float)
        err = np.full_like(flux, np.nan) if err is None else np.asarray(err, float)
        ok = np.isfinite(wave) & np.isfinite(flux) & (flux != 0)
        for lo, hi in tuple(TELLURIC) + tuple(mask):
            ok &= ~((wave >= lo) & (wave <= hi))
        gw = vac_to_air(grid.wave) if air else grid.wave
        ok &= (wave > gw[0] + 15) & (wave < gw[-1] - 15)  # room for the velocity shift
        if ok.sum() < 50:
            raise ValueError("the grid does not cover this spectrum's wavelengths")
        self.wave, self.flux = wave[ok], flux[ok]
        e = err[ok]
        if not np.all(np.isfinite(e) & (e > 0)):  # no errors given: from the point-to-point scatter
            noise = 1.4826 * np.median(np.abs(np.diff(self.flux))) / np.sqrt(2)
            e = np.full_like(self.flux, noise if noise > 0 else np.std(self.flux))
        self.err = e
        self.grid, self.gwave, self.resolution = grid, gw, float(resolution)
        self.dv = C_KMS * np.median(np.diff(np.log(gw)))
        edges = np.arange(self.wave[0], self.wave[-1] + chunk, chunk)
        self.chunks = [
            np.flatnonzero((self.wave >= a) & (self.wave < b)) for a, b in zip(edges[:-1], edges[1:], strict=True)
        ]
        self.chunks = [c for c in self.chunks if len(c) > 3 * (degree + 1)]
        self.degree = degree

    def broadened(self, teff, logg, feh, vsini):
        s = self.grid.spectrum(teff, logg, feh)
        k = self._conv(rotation_kernel(vsini, self.dv), gauss_kernel(C_KMS / self.resolution, self.dv))
        pad = len(k) // 2
        return self._conv(np.pad(s, pad, mode="edge"), k, mode="valid")

    def model(self, p):
        teff, logg, feh, vsini, rv = p
        return self.shifted(self.broadened(teff, logg, feh, max(vsini, 0.0)), rv)

    def shifted(self, s, rv):
        """A broadened grid spectrum moved by rv and multiplied by the best continuum polynomial of each chunk."""
        m = np.interp(self.wave, self.gwave * (1 + rv / C_KMS), s)
        out = np.empty_like(m)
        for c in self.chunks:
            x = (self.wave[c] - self.wave[c].mean()) / np.ptp(self.wave[c])
            a = m[c][:, None] * np.vander(x, self.degree + 1) / self.err[c][:, None]
            coef = np.linalg.lstsq(a, self.flux[c] / self.err[c], rcond=None)[0]
            out[c] = m[c] * np.polyval(coef, x)
        return out

    def residuals(self, p):
        idx = np.concatenate(self.chunks)
        return ((self.flux - self.model(p)) / self.err)[idx]

    def chi2(self, p):
        return float(np.sum(self.residuals(p) ** 2))


def fit(wave, flux, err, grid, resolution, air=True, vsini_start=None, rv_range=(-400.0, 400.0), mask=()):
    """Teff, log g, [Fe/H], v sin i, RV with 1-sigma errors, chi2_red, the best grid point, and the model."""
    from scipy.optimize import least_squares

    f = Fitter(wave, flux, err, grid, resolution, air=air, mask=mask)
    lo, hi = grid.bounds()
    centre = np.array([np.median(a) for a in grid.axes])
    span = np.array([max(np.ptp(a), 1e-9) for a in grid.axes])
    mid = min(grid.spectra, key=lambda k: np.sum(((np.array(k) - centre) / span) ** 2))  # an existing point
    v0 = 5.0 if vsini_start is None else float(vsini_start)
    s_mid = f.broadened(*mid, v0)
    idx = np.concatenate(f.chunks)
    rvs = np.arange(rv_range[0], rv_range[1] + 1e-9, max(1.0, C_KMS / resolution / 3))
    rv0 = rvs[int(np.argmin([np.sum(((f.flux - f.shifted(s_mid, rv)) / f.err)[idx] ** 2) for rv in rvs]))]
    best = (np.inf, None)
    for key in grid.spectra:
        for vs in [v0] if vsini_start is not None else (3.0, 10.0, 30.0, 80.0):
            c2 = f.chi2((*key, vs, rv0))
            if c2 < best[0]:
                best = (c2, (*key, vs, rv0))
    start = np.array(best[1], float)
    scale = np.array([100.0, 0.2, 0.1, 2.0, 1.0])
    hi = [max(h, low + 1e-6) for low, h in zip(lo, hi, strict=True)]  # an axis with one value stays at it
    bounds = (np.r_[lo, 0.0, rv_range[0]], np.r_[hi, 500.0, rv_range[1]])
    start = np.clip(start, bounds[0] + 1e-9, bounds[1] - 1e-9)
    r = least_squares(f.residuals, start, bounds=bounds, x_scale=scale, diff_step=1e-4)
    n, k = r.fun.size, 5
    chi2_red = float(np.sum(r.fun**2) / max(1, n - k - len(f.chunks) * (f.degree + 1)))
    try:
        cov = np.linalg.inv(r.jac.T @ r.jac) * max(chi2_red, 1e-12)
        errs = np.sqrt(np.clip(np.diag(cov), 0, None))
    except np.linalg.LinAlgError:
        errs = np.full(5, np.nan)
    names = ("teff", "logg", "feh", "vsini", "rv")
    out = {k: float(v) for k, v in zip(names, r.x, strict=True)}
    out["errors"] = {k: float(v) for k, v in zip(names, errs, strict=True)}
    edge = [n for n, v, a, b in zip(names[:3], r.x[:3], lo, hi, strict=True) if np.isclose(v, a) or np.isclose(v, b)]
    out |= {"chi2_red": chi2_red, "n": int(n), "start": [float(v) for v in start], "at_edge": edge}
    out["wave"], out["flux"], out["model"] = f.wave.tolist(), f.flux.tolist(), f.model(r.x).tolist()
    return out


def neighbourhood(teff, logg, feh, axes=None, width=1):
    """Grid points within `width` steps of (teff, logg, feh) on every axis (PHOENIX axes by default)."""
    axes = axes or phoenix_axes()
    pick = []
    for a, v in zip(axes, (teff, logg, feh), strict=True):
        i = int(np.argmin(np.abs(a - v)))
        pick.append(a[max(0, i - width) : i + width + 1])
    return [(float(t), float(g), float(z)) for t in pick[0] for g in pick[1] for z in pick[2]]


def coarse_nodes():
    """A first, coarse set of PHOENIX points for an unknown star: Teff 3500-7000 K every 500 K and 7600 K (above
    7000 K the grid steps by 200 K), log g 2.5 and 4.5, solar metallicity."""
    return [(float(t), g, 0.0) for t in [*range(3500, 7001, 500), 7600] for g in (2.5, 4.5)]


# --- the Sun as the reference ---------------------------------------------------------------------------------------
SUN = {"teff": 5772.0, "logg": 4.438, "feh": 0.0}  # IAU 2015 Resolution B3 nominal Teff; log g = log(GM/R^2)
KURUCZ_SUN = "http://kurucz.harvard.edu/sun/fluxatlas2005/fluxspliced.2005"


def download_sun(folder, fetch=None):
    """The Kurucz (2005) solar flux atlas (air wavelengths), kept as 3000-10000 A on the grids' ln(lambda) step.
    Returns (wave, flux)."""
    path = Path(folder) / "sun_kurucz2005.npz"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        text = (fetch or _fetch)(KURUCZ_SUN).decode("ascii", "replace").splitlines()[1:]
        d = np.array([[float(v) for v in line.split()[:2]] for line in text if line.strip()])
        w, f = d[:, 0] * 10, d[:, 1]  # nm -> A
        out = store_wave()
        out = out[(out > w[0]) & (out < w[-1])]
        np.savez_compressed(path, wave=out, flux=_rebin(w, f, out).astype(np.float32))
    d = np.load(path)
    return d["wave"], d["flux"].astype(float)


def degrade(wave, flux, resolution, out_wave):
    """A high-resolution spectrum brought to a spectrograph's resolution and sampled at out_wave."""
    step = 1 / (10 * resolution)
    lw = np.arange(np.log(wave[0]), np.log(wave[-1]), step)
    k = gauss_kernel(C_KMS / resolution, C_KMS * step)
    f = np.convolve(np.pad(np.interp(lw, np.log(wave), flux), len(k) // 2, mode="edge"), k, mode="valid")
    return np.interp(np.log(out_wave), lw, f)


def solar_mask(f_sun, threshold=0.02):
    """Wavelength intervals where the grid at the Sun's parameters does not reproduce the solar spectrum within
    `threshold` (fraction of the median flux), widened by one resolution element; v sin i and RV fitted first."""
    from scipy.optimize import least_squares

    sun = (SUN["teff"], SUN["logg"], SUN["feh"])
    r = least_squares(lambda p: f_sun.residuals((*sun, p[0], p[1])), [3.0, 0.0], bounds=([0, -50], [100, 50]))
    bad = np.abs(f_sun.flux - f_sun.model((*sun, *r.x))) / np.median(f_sun.flux) > threshold
    fwhm_px = (C_KMS / f_sun.resolution) / (C_KMS * np.median(np.diff(np.log(f_sun.wave))))
    half = max(1, int(np.ceil(fwhm_px)))
    bad = np.convolve(bad.astype(int), np.ones(2 * half + 1, int), mode="same") > 0
    edges = np.flatnonzero(np.diff(np.r_[0, bad.astype(int), 0]))
    w = f_sun.wave
    return [(float(w[s]) - 1e-3, float(w[e - 1]) + 1e-3) for s, e in zip(edges[::2], edges[1::2], strict=True)]


# interpolation between grid points, measured in tests/test_atmosphere.py; added to the statistical errors
FLOOR = {"teff": 15.0, "logg": 0.04, "feh": 0.02}


def solar_reference(wave, sun_wave, sun_flux, sun_grid, resolution, sun_degraded=False, air=True, mask=()):
    """The Sun seen like the star: on its pixels, at its resolution. Returns the mask (wavelengths the grid does
    not reproduce in the Sun) and the Sun's fitted parameters minus its known ones.
    sun_wave, sun_flux: the solar atlas (brought to `resolution` here) or a solar spectrum taken with the same
    spectrograph (sun_degraded=True)."""
    wave = np.asarray(wave, float)
    sun = np.interp(wave, sun_wave, sun_flux) if sun_degraded else degrade(sun_wave, sun_flux, resolution, wave)
    smask = list(mask) + solar_mask(Fitter(wave, sun, None, sun_grid, resolution, air=air, mask=mask))
    s = fit(wave, sun, None, sun_grid, resolution, air=air, mask=smask)
    return {
        "mask": smask,
        "offsets": {k: s[k] - SUN[k] for k in ("teff", "logg", "feh")},
        "errors": {k: s["errors"][k] for k in ("teff", "logg", "feh")},
        "fit": {k: s[k] for k in ("teff", "logg", "feh", "vsini", "rv", "chi2_red")},
    }


def analyse(wave, flux, err, grid, resolution, ref, air=True):
    """The star relative to the Sun (see the module notes; ref from solar_reference). Returns the star's fit with
    "teff", "logg", "feh" on the Sun's scale (errors: star, Sun and interpolation combined), the raw values, the
    Sun's offsets, the fraction of pixels used and a flag for stars far from the Sun."""
    star = fit(wave, flux, err, grid, resolution, air=air, mask=ref["mask"])
    out = dict(star)
    out["raw"] = {k: star[k] for k in ("teff", "logg", "feh")}
    out["sun_offsets"], out["sun_fit"] = ref["offsets"], ref["fit"]
    out["errors"] = dict(star["errors"])
    for k in ("teff", "logg", "feh"):
        out[k] = star[k] - ref["offsets"][k]
        out["errors"][k] = float(np.sqrt(star["errors"][k] ** 2 + ref["errors"][k] ** 2 + FLOOR[k] ** 2))
    used = Fitter(wave, flux, err, grid, resolution, air=air, mask=ref["mask"])
    out["used_fraction"] = float(sum(len(c) for c in used.chunks) / max(1, np.isfinite(flux).sum()))
    out["far_from_sun"] = bool(
        abs(out["teff"] - SUN["teff"]) > 800 or abs(out["logg"] - SUN["logg"]) > 1.0 or abs(out["feh"]) > 0.7
    )
    return out
