"""Wavelength calibration from an arc-lamp spectrum.

1. Lines in the extracted arc: peaks above a threshold, centred with a Gaussian fit.
2. A first solution from at least two (pixel, wavelength) pairs the user identifies (or a
   linear guess of start wavelength and dispersion).
3. Iteratively: predict every catalogue line's pixel, match peaks within a tolerance, fit a
   polynomial with sigma clipping, tighten. The result reports the RMS in Angstrom and the
   lines used, so a bad solution is visible, not silent.

Line lists: the IRAF lists (air wavelengths, BSD-3, from astropy/specreduce-data) are shipped
in resources/linelists.
"""

import warnings
from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path

import numpy as np
from scipy.optimize import OptimizeWarning, curve_fit
from scipy.signal import find_peaks

LINELIST_DIR = Path(str(files("astrowb") / "resources" / "linelists"))


def line_lists() -> list[str]:
    return sorted(p.stem for p in LINELIST_DIR.glob("*.dat"))


def load_line_list(name: str) -> np.ndarray:
    """Wavelengths (Angstrom, air) of an IRAF line list."""
    waves = []
    for line in (LINELIST_DIR / f"{name}.dat").read_text().splitlines():
        parts = line.split("#", 1)[0].split()
        if parts:
            try:
                waves.append(float(parts[0]))
            except ValueError:
                continue
    return np.array(sorted(waves))


def _gauss(x, a, mu, s, c):
    return a * np.exp(-0.5 * ((x - mu) / s) ** 2) + c


def find_lines(arc, fwhm=3.0, snr=5.0):
    """Pixel centres (sub-pixel) of emission lines in a 1-D arc spectrum."""
    arc = np.nan_to_num(np.asarray(arc, float))
    base = np.median(arc)
    noise = 1.4826 * np.median(np.abs(arc - base))
    peaks, _ = find_peaks(arc, height=base + snr * max(noise, 1e-9), distance=max(2, int(fwhm)))
    centres = []
    x = np.arange(len(arc))
    hw = int(np.ceil(1.5 * fwhm))
    for p in peaks:
        lo, hi = max(0, p - hw), min(len(arc), p + hw + 1)
        if hi - lo < 6:  # four parameters need more pixels than that (a line cut by the edge of the array)
            continue
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", OptimizeWarning)  # judged below by the covariance itself
                popt, pcov = curve_fit(
                    _gauss, x[lo:hi], arc[lo:hi], p0=[arc[p] - base, p, fwhm / 2.355, base], maxfev=2000
                )
        except (RuntimeError, ValueError):
            continue
        sigma = abs(popt[2])
        # a centre without an error estimate, or a "line" much narrower or wider than the lines is not used
        if abs(popt[1] - p) < hw and np.isfinite(pcov[1, 1]) and 0.15 * fwhm < 2.355 * sigma < 4 * fwhm:
            centres.append(popt[1])
    return np.array(centres)


@dataclass
class Solution:
    coef: np.ndarray  # numpy.polyval order, pixel -> Angstrom
    rms: float  # Angstrom
    pixels: np.ndarray = field(default_factory=lambda: np.array([]))
    waves: np.ndarray = field(default_factory=lambda: np.array([]))
    degree: int | None = None  # chosen from the lines (leave-one-out)

    def __call__(self, pixel):
        return np.polyval(self.coef, pixel)

    @property
    def n_lines(self):
        return len(self.pixels)


def _match(pred, catalogue, tol):
    """Index of the nearest catalogue line for each prediction, and which matches to keep
    (within tol, one peak per line: the closest)."""
    idx = np.clip(np.searchsorted(catalogue, pred), 1, len(catalogue) - 1)
    nearest = np.where(np.abs(catalogue[idx - 1] - pred) < np.abs(catalogue[idx] - pred), idx - 1, idx)
    dist = np.abs(catalogue[nearest] - pred)
    ok = dist < tol
    for line in np.unique(nearest[ok]):
        same = ok & (nearest == line)
        if same.sum() > 1:
            ok[same] = False
            ok[np.where(same)[0][np.argmin(dist[same])]] = True
    return nearest, ok


def _degree(order, n):
    """As many terms as the lines carry: at least four more lines than coefficients (a cubic through four lines has
    no residual and says nothing; nine EFOSC2 He-Ar lines need the quartic, 0.2 A rms against 1 A for a cubic)."""
    return int(min(order, max(1, n - 4)))


def _clipped_fit(px, wv, deg, clip):
    keep = np.ones(len(px), bool)
    for _ in range(5):
        coef = np.polyfit(px[keep], wv[keep], deg)
        resid = wv - np.polyval(coef, px)
        sd = np.std(resid[keep])
        new = np.abs(resid) < clip * max(sd, 1e-6)
        if np.array_equal(new, keep) or new.sum() <= deg + 1:
            break
        keep = new
    return coef, keep, sd


def solve(peaks, catalogue, guesses, order=3, tolerance=None, clip=3.0, grow=0.05):
    """guesses: [(pixel, wavelength), ...] (>= 2). Returns a Solution or raises ValueError.

    Lines are matched first between the identified ones, where the first (linear) solution is
    good, then the window grows outwards by `grow` of the pixel range per step, refitting each
    time, so curved dispersions are followed instead of extrapolated (steps of 15 % let the curve of EFOSC2 grism 11
    run 27 A off in the blue: five correct lines by hand gave 3 A rms; with 5 % two lines are enough for 0.21 A)."""
    peaks, catalogue = np.sort(np.asarray(peaks, float)), np.sort(np.asarray(catalogue, float))
    g = np.asarray(guesses, float)
    if len(g) < 2:
        raise ValueError("identify at least two lines")
    coef = np.polyfit(g[:, 0], g[:, 1], min(len(g) - 1, order))
    disp = abs(np.polyval(np.polyder(coef), g[:, 0].mean()))
    tol = tolerance or 2 * disp  # Angstrom
    # catalogue lines with a neighbour closer than the tolerance cannot be told apart at this resolution (a He-Ar
    # list at 4 A per pixel: blended Ar lines were matched as single ones and the EFOSC2 solution had 1.1 A rms);
    # the lines the user identified are always kept
    gap = np.diff(catalogue)
    alone = np.r_[True, gap > tol] & np.r_[gap > tol, True]
    catalogue = np.unique(np.r_[catalogue[alone], g[:, 1]])
    lo, hi = g[:, 0].min(), g[:, 0].max()
    span = peaks.max() - peaks.min()
    # the identified lines stay what the user said they are (IRAF identify keeps them; only new lines are added): a
    # PESSTO identification of He I 3888.7 was moved to 3928.6 by the matching and the EFOSC2 solution had 5 A rms
    anchors = [(int(np.argmin(np.abs(peaks - p))), w) for p, w in g if np.min(np.abs(peaks - p)) <= 2.0]

    def match(pred, tolerance):
        nearest, ok = _match(pred, catalogue, tolerance)
        for i, w in anchors:
            nearest[i], ok[i] = int(np.searchsorted(catalogue, w)), True
        return nearest, ok

    while True:
        inside = (peaks >= lo) & (peaks <= hi)
        nearest, ok = match(np.polyval(coef, peaks), tol)
        ok &= inside
        deg = _degree(order, ok.sum())
        if ok.sum() <= deg + 1:
            raise ValueError("too few lines matched: check the identified lines and the line list")
        px, wv = peaks[ok], catalogue[nearest[ok]]
        coef, keep, sd = _clipped_fit(px, wv, deg, clip)
        if lo <= peaks.min() and hi >= peaks.max():
            break
        lo, hi = lo - grow * span, hi + grow * span
    for _ in range(3):  # final passes over all lines with a tightened tolerance
        nearest, ok = match(np.polyval(coef, peaks), max(3 * sd, 0.3 * disp))
        px, wv = peaks[ok], catalogue[nearest[ok]]
        deg = _best_degree(px, wv, _degree(order, len(px)))
        if len(px) <= deg + 1:
            raise ValueError("too few lines matched: check the identified lines and the line list")
        coef, keep, sd = _clipped_fit(px, wv, deg, clip)
    resid = wv[keep] - np.polyval(coef, px[keep])
    return Solution(coef, float(np.sqrt(np.mean(resid**2))), px[keep], wv[keep], len(coef) - 1)


def _best_degree(px, wv, highest):
    """The degree whose fit predicts each line best from the others (leave-one-out), up to `highest`: a quartic
    only when it really does better (EFOSC2 grism 11: 0.21 A against 0.97 A for the cubic), a straight line for a
    grating that is straight."""
    best, best_err = 1, np.inf
    for d in range(1, highest + 1):
        err = []
        for i in range(len(px)):
            rest = np.arange(len(px)) != i
            err.append(wv[i] - np.polyval(np.polyfit(px[rest], wv[rest], d), px[i]))
        loo = float(np.sqrt(np.mean(np.square(err))))
        if loo < 0.95 * best_err:  # a higher degree must do clearly better
            best, best_err = d, loo
    return best


# Night-sky emission lines (air, Angstrom) for the zero point of a long-slit spectrum: the arc is often taken hours
# before or after, and the spectrograph flexes in between (a real EFOSC2 night: [O I] 5577, 6300 and 6363 all 8.4 A
# off, the same in every line). Pipelines shift the solution by the sky lines' offset; so does this.
SKY_LINES = (5577.338, 6300.304, 6363.776)


def sky_shift(wave, sky, min_snr=8.0, strong_snr=15.0):
    """The offset (A) of the night-sky lines in the extracted sky, or None when the lines do not tell it safely:
    each line counts above min_snr; the offset is used when two lines agree (within 3 sigma) or one has
    strong_snr. Returns (offset or None, [(line, offset, error, snr)])."""
    from scipy.optimize import curve_fit

    wave, sky = np.asarray(wave, float), np.asarray(sky, float)
    disp = float(np.median(np.abs(np.diff(wave))))

    def model(x, a, mu, s, b, k):
        return b + k * (x - mu) + a * np.exp(-0.5 * ((x - mu) / s) ** 2)

    found = []
    for lab in SKY_LINES:
        m = np.isfinite(sky) & (wave > lab - 8 * disp) & (wave < lab + 8 * disp)
        if m.sum() < 10:
            continue
        # offsets from the line, not wavelengths of ~5577 A: at echelle dispersion (0.03 A/px) the fit in absolute
        # wavelengths did not converge
        y, x = sky[m], wave[m] - lab
        start = [np.ptp(y), float(x[np.argmax(y)]), 1.5 * disp, np.median(y), 0.0]
        try:
            p, cov = curve_fit(model, x, y, p0=start, maxfev=4000)
        except (RuntimeError, ValueError):
            continue
        noise = 1.4826 * np.median(np.abs(y - model(x, *p)))  # from the fit: the line's own slope is not noise
        err = float(np.sqrt(cov[1, 1])) if np.isfinite(cov[1, 1]) else np.inf
        snr = float(p[0] / noise) if noise > 0 else 0.0
        if snr >= min_snr and 0.3 * disp < abs(p[2]) < 6 * disp and abs(p[1]) < 6 * disp and err < disp:
            found.append((lab, float(p[1]), err, snr))
    return combine_sky(found, disp, strong_snr), found


def combine_sky(found, disp, strong_snr=15.0):
    """The zero-point offset from measured sky lines [(line, offset, error, snr)], or None: two or more lines that
    agree within 3 sigma (weighted mean), or a single line of strong_snr."""
    if not found:
        return None
    off = np.array([f[1] for f in found])
    err = np.array([f[2] for f in found])
    if len(found) == 1:
        return found[0][1] if found[0][3] >= strong_snr else None
    mean = float(np.sum(off / err**2) / np.sum(1 / err**2))
    if np.all(np.abs(off - mean) < 3 * np.hypot(err, 0.1 * disp)):
        return mean
    return None


def sky_shift_orders(waves, skies, min_snr=8.0, strong_snr=15.0):
    """sky_shift over the orders of an echelle spectrum: each night-sky line measured in every order that holds it
    (an order's ends are left out), then combined as for a long slit. Returns (offset or None, found)."""
    found, disps = [], []
    for w, sky in zip(waves, skies, strict=True):
        w = np.asarray(w, float)
        lo, hi = np.nanmin(w), np.nanmax(w)
        if not any(lo + 0.05 * (hi - lo) < lab < hi - 0.05 * (hi - lo) for lab in SKY_LINES):
            continue
        _, f = sky_shift(w, sky, min_snr, strong_snr)
        found += f
        disps.append(float(np.median(np.abs(np.diff(w)))))
    return combine_sky(found, float(np.median(disps)) if disps else 1.0, strong_snr), found
