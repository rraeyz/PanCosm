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


def solve(peaks, catalogue, guesses, order=3, tolerance=None, clip=3.0, grow=0.15):
    """guesses: [(pixel, wavelength), ...] (>= 2). Returns a Solution or raises ValueError.

    Lines are matched first between the identified ones, where the first (linear) solution is
    good, then the window grows outwards by `grow` of the pixel range per step, refitting each
    time, so curved dispersions are followed instead of extrapolated."""
    peaks, catalogue = np.sort(np.asarray(peaks, float)), np.sort(np.asarray(catalogue, float))
    g = np.asarray(guesses, float)
    if len(g) < 2:
        raise ValueError("identify at least two lines")
    coef = np.polyfit(g[:, 0], g[:, 1], min(len(g) - 1, order))
    disp = abs(np.polyval(np.polyder(coef), g[:, 0].mean()))
    tol = tolerance or 2 * disp  # Angstrom
    lo, hi = g[:, 0].min(), g[:, 0].max()
    span = peaks.max() - peaks.min()
    while True:
        inside = (peaks >= lo) & (peaks <= hi)
        nearest, ok = _match(np.polyval(coef, peaks), catalogue, tol)
        ok &= inside
        deg = int(min(order, max(1, ok.sum() // 4)))
        if ok.sum() <= deg + 1:
            raise ValueError("too few lines matched: check the identified lines and the line list")
        px, wv = peaks[ok], catalogue[nearest[ok]]
        coef, keep, sd = _clipped_fit(px, wv, deg, clip)
        if lo <= peaks.min() and hi >= peaks.max():
            break
        lo, hi = lo - grow * span, hi + grow * span
    for _ in range(3):  # final passes over all lines with a tightened tolerance
        nearest, ok = _match(np.polyval(coef, peaks), catalogue, max(3 * sd, 0.3 * disp))
        px, wv = peaks[ok], catalogue[nearest[ok]]
        # as many terms as the lines carry: a cubic through four lines has no residual and says nothing
        deg = int(min(order, max(1, len(px) // 4)))
        if len(px) <= deg + 1:
            raise ValueError("too few lines matched: check the identified lines and the line list")
        coef, keep, sd = _clipped_fit(px, wv, deg, clip)
    resid = wv[keep] - np.polyval(coef, px[keep])
    return Solution(coef, float(np.sqrt(np.mean(resid**2))), px[keep], wv[keep])
