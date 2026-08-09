"""Echelle (and other multi-order: cross-dispersed, fibre-fed, coudé) spectra.

Dispersion runs along x, orders are stacked along y. Every function takes plain arrays.

find_orders:  peaks of the cross-section of a flat (or bright star) near the central column.
trace_orders: each order followed outwards from the centre column bin by bin (orders are tilted
              and curved, so the search window moves with the order), then a clipped polynomial.
extract:      boxcar or Horne optimal extraction (longslit.optimal) per order, sky from the gaps.
blaze:        the extracted flat smoothed along the order and normalised to 1 at its peak.
solve_2d:     global wavelength solution from the grating equation: m * lambda is a smooth
              function of x and m alone, fitted as sum c_ij x^i m^j (IRAF ecidentify approach,
              Baranne et al. 1996). A few identified lines in a few orders start it; matching then
              grows over all orders' arc lines with clipping.
merge:        blaze-corrected orders resampled onto one log-lambda grid, inverse-variance weighted
              where orders overlap.
scattered_light: light scattered inside the spectrograph (IRAF apscatter): medians in the gaps between
              the orders, a clipped polynomial across the dispersion in every column band, then smoothed
              along the dispersion; subtracted from the frame before extraction.
"""

from dataclasses import dataclass, field

import numpy as np
from scipy.ndimage import median_filter
from scipy.signal import find_peaks, savgol_filter

from . import longslit


def find_orders(flat, min_separation=6, snr=10.0, band=21):
    """Rows of the orders at the central column (sub-pixel, ascending)."""
    ny, nx = flat.shape
    c = nx // 2
    cut = np.nanmedian(flat[:, max(0, c - band // 2) : c + band // 2 + 1], axis=1)
    base = np.nanpercentile(cut, 5)
    noise = 1.4826 * np.nanmedian(np.abs(np.diff(cut))) / np.sqrt(2) + 1e-9
    peaks, props = find_peaks(cut - base, height=snr * noise, distance=min_separation, prominence=snr * noise)
    # neighbouring orders differ little in brightness; a bump a tenth of its neighbour or fainter is the other
    # fibre's light leaking in or a ghost (a real HARPS fibre-A flat: 33-119 ADU beside orders of 2000-25000)
    prom, keep = props["prominences"], np.ones(len(peaks), bool)
    while keep.sum() > 1:
        idx = np.flatnonzero(keep)
        p = prom[idx]
        weak = p < 0.1 * np.maximum(np.r_[0.0, p[:-1]], np.r_[p[1:], 0.0])
        if not weak.any():
            break
        keep[idx[weak]] = False
    peaks = peaks[keep]
    rows = []
    for p in peaks:  # parabola through the three highest samples
        if 0 < p < ny - 1:
            a, b, d = cut[p - 1], cut[p], cut[p + 1]
            den = a - 2 * b + d
            rows.append(p + (0.5 * (a - d) / den if den != 0 else 0.0))
    return np.array(rows)


def _centroid(image, x_lo, x_hi, guess, half):
    ny = image.shape[0]
    lo, hi = int(max(0, round(guess - half))), int(min(ny, round(guess + half) + 1))
    if hi - lo < 3:
        return None
    cut = np.nanmedian(image[lo:hi, x_lo:x_hi], axis=1)
    cut = cut - np.nanmin(cut)
    if cut.sum() <= 0:
        return None
    return lo + float(np.sum(np.arange(len(cut)) * cut) / cut.sum())


def trace_orders(flat, rows=None, n_bins=64, order=4, clip=3.0, half_window=None):
    """Polynomial coefficients y(x) (numpy.polyval order) for each order of a flat."""
    rows = find_orders(flat) if rows is None else np.asarray(rows, float)
    if len(rows) == 0:
        raise ValueError(
            "no orders found: check that the flat shows the orders as bright stripes, or add them by hand on the flat"
        )
    nx = flat.shape[1]
    half = half_window or order_window(rows)
    edges = np.linspace(0, nx, n_bins + 1).astype(int)
    centres = (edges[:-1] + edges[1:] - 1) / 2
    start = int(np.argmin(np.abs(centres - nx / 2)))
    coefs = []
    for row in rows:
        ys = np.full(n_bins, np.nan)
        for direction in (range(start, n_bins), range(start - 1, -1, -1)):
            guess, slope, last = row, 0.0, None
            for i in direction:
                pred = guess if last is None else guess + slope * (centres[i] - centres[last])
                y = _centroid(flat, edges[i], edges[i + 1], pred, half)
                if y is None or abs(y - pred) > half / 2:
                    continue  # lost in a gap or a defect: keep the prediction, try the next bin
                if last is not None:
                    slope = (y - guess) / (centres[i] - centres[last])
                ys[i], guess, last = y, y, i
        ok = np.isfinite(ys)
        if ok.sum() < order + 2:
            raise ValueError(f"order at row {row:.1f} could not be traced")
        xs, yv = centres[ok], ys[ok]
        keep = np.ones(len(xs), bool)
        for _ in range(5):
            coef = np.polyfit(xs[keep], yv[keep], order)
            resid = yv - np.polyval(coef, xs)
            new = np.abs(resid) < clip * max(np.std(resid[keep]), 1e-3)
            if np.array_equal(new, keep) or new.sum() < order + 2:
                break
            keep = new
        coefs.append(coef)
    return coefs


def order_window(rows):
    """Half-width of the search window for tracing, from the spacing of all the orders."""
    rows = np.sort(np.asarray(rows, float))
    sep = np.median(np.diff(rows)) if len(rows) > 1 else 20.0
    return max(2.0, 0.4 * sep)


def trace_each(flat, rows):
    """Trace the orders one by one: (rows of the traced orders at the central column, read from their traces so a
    rough click is refined; their coefficients; rows that could not be traced). The search window comes from the
    spacing of all the given rows, as in trace_orders."""
    rows = np.sort(np.asarray(rows, float))
    half = order_window(rows)
    kept, coefs, failed = [], [], []
    for row in rows:
        try:
            coefs.append(trace_orders(flat, [row], half_window=half)[0])
            kept.append(float(np.polyval(coefs[-1], flat.shape[1] // 2)))
        except ValueError:
            failed.append(float(row))
    return kept, coefs, failed


def row_at_centre(coefs, x, y, nx):
    """The row at the central column of an order clicked at (x, y): moved along the curvature of the nearest
    traced order (orders are nearly parallel), so a missed order can be added by clicking anywhere on it."""
    if not len(coefs):
        return float(y)
    near = min(coefs, key=lambda c: abs(np.polyval(c, x) - y))
    return float(y + np.polyval(near, nx / 2) - np.polyval(near, x))


def _gaps(coefs, nx):
    """Half the distance to the nearest neighbouring order, per order (pixels, at the centre)."""
    yc = np.array([np.polyval(c, nx / 2) for c in coefs])
    d = np.abs(np.diff(yc))
    left = np.r_[d[:1], d] if len(d) else np.array([20.0])
    right = np.r_[d, d[-1:]] if len(d) else np.array([20.0])
    return 0.5 * np.minimum(left, right)


def profile_fwhm(image, coefs, band=21):
    """Median full width at half maximum (pixels) of the orders across the dispersion at the central columns, or
    None. The half-maximum crossings beside the peak: another fibre's light a little further out does not count."""
    ny, nx = image.shape
    c = nx // 2
    cols = np.asarray(image[:, max(0, c - band // 2) : c + band // 2 + 1], float)
    out = []
    for coef, g in zip(coefs, _gaps(coefs, nx), strict=True):
        y0 = np.polyval(coef, c)
        p = np.nanmedian(cols[int(max(0, y0 - g)) : int(min(ny, y0 + g + 1))], axis=1)
        if len(p) < 5:
            continue
        p = p - np.nanmin(p)
        k = int(np.nanargmax(p))
        half = p[k] / 2
        lo, hi = k, k
        while lo > 0 and p[lo - 1] > half:
            lo -= 1
        while hi < len(p) - 1 and p[hi + 1] > half:
            hi += 1
        if half > 0 and 0 < lo and hi < len(p) - 1:
            out.append(hi + (p[hi] - half) / (p[hi] - p[hi + 1]) - lo + (p[lo] - half) / (p[lo] - p[lo - 1]))
    return float(np.median(out)) if out else None


def extract(image, coefs, width=None, method="optimal", subtract_sky=True, gain=1.0, read_noise=5.0):
    """Return (flux, error) arrays of shape (n_orders, nx). The width (pixels; e.g. 3 x profile_fwhm) is at most
    70 % of the order spacing, which it is by default; the sky comes from the inter-order gaps (set
    subtract_sky=False for arcs and for fibres without gaps)."""
    image = np.asarray(image, float)
    nx = image.shape[1]
    gaps = _gaps(coefs, nx)
    flux, err = np.zeros((len(coefs), nx)), np.zeros((len(coefs), nx))
    for k, coef in enumerate(coefs):
        w = max(3.0, min(width or np.inf, 1.4 * gaps[k]))
        off = w / 2 + max(1.0, 0.25 * (2 * gaps[k] - w))
        sky_w = max(1.0, 2 * gaps[k] - off - 0.5)
        if method == "optimal" and subtract_sky:
            f, e, _, _ = longslit.optimal(image, coef, w, off, sky_w, gain, read_noise)
        else:
            f, sky = longslit.boxcar(image, coef, w, off, sky_w, subtract_sky)
            n_pix = w + 1
            e = np.sqrt(np.clip(f + n_pix * sky, 0, None) / gain + n_pix * read_noise**2 / gain**2)
        flux[k], err[k] = f, e
    return flux, err


def blaze(flat_flux, window=101):
    """Smoothed, peak-normalised blaze function per order from extracted flat spectra."""
    out = np.empty_like(np.asarray(flat_flux, float))
    for k, f in enumerate(flat_flux):
        f = median_filter(np.nan_to_num(f), size=min(window // 4 * 2 + 1, len(f)))
        win = min(window, len(f) - (1 - len(f) % 2))
        s = savgol_filter(f, win, 3) if win > 5 else f
        out[k] = np.clip(s / max(np.nanmax(s), 1e-12), 0, None)
    return out


@dataclass
class EchelleSolution:
    coef: np.ndarray  # c[i, j]: m * lambda = sum c_ij u^i v^j with u, v scaled x and m
    x_scale: tuple
    m_scale: tuple
    rms: float  # Angstrom
    n_lines: int
    orders: np.ndarray = field(default_factory=lambda: np.array([]))  # absolute order numbers
    lines: list = field(default_factory=list)  # [order, pixel, catalogue wavelength, residual (A), used]

    def _uv(self, x, m):
        return (np.asarray(x, float) - self.x_scale[0]) / self.x_scale[1], (
            np.asarray(m, float) - self.m_scale[0]
        ) / self.m_scale[1]

    def __call__(self, x, m):
        """Wavelength (Angstrom) at pixel x in absolute order m."""
        x, m = np.broadcast_arrays(np.asarray(x, float), np.asarray(m, float))
        u, v = self._uv(x, m)
        return np.polynomial.polynomial.polyval2d(u, v, self.coef) / m

    def wavelengths(self, nx):
        """(n_orders, nx) wavelength array for the traced orders."""
        x = np.arange(nx)
        return np.array([self(x, m) for m in self.orders])


def _fit_2d(x, m, mlam, deg_x, deg_m, xs, ms, clip=3.0):
    u, v = (x - xs[0]) / xs[1], (m - ms[0]) / ms[1]
    terms = [(i, j) for i in range(deg_x + 1) for j in range(deg_m + 1)]
    a = np.column_stack([u**i * v**j for i, j in terms])
    keep = np.ones(len(x), bool)
    for _ in range(6):
        sol, *_ = np.linalg.lstsq(a[keep], mlam[keep], rcond=None)
        resid = (mlam - a @ sol) / m  # Angstrom
        r = resid[keep]
        scale = 1.4826 * np.median(np.abs(r - np.median(r)))  # robust: wrong pairs do not widen the clip
        new = np.abs(resid) < clip * max(scale, 1e-6)
        if np.array_equal(new, keep) or new.sum() <= len(terms):
            break
        keep = new
    sd = float(np.std(resid[keep]))
    c = np.zeros((deg_x + 1, deg_m + 1))
    for (i, j), s in zip(terms, sol, strict=True):
        c[i, j] = s
    return c, keep, sd


def solve_2d(peaks, orders, catalogue, guesses, deg_x=4, deg_m=3, clip=3.0, nx=None, exclude=()):
    """Global echelle wavelength solution.

    peaks:     list (one per traced order) of arc-line pixel positions (wavecal.find_lines).
    orders:    absolute order number m of each traced order.
    catalogue: line wavelengths (Angstrom), e.g. wavecal.load_line_list("thar").
    guesses:   [(m, pixel, wavelength), ...] identified lines, at least 4, in at least 2 orders.
    exclude:   [(m, pixel), ...] arc lines left out by hand (as deleting a point in IRAF ecidentify).
    """
    catalogue = np.sort(np.asarray(catalogue, float))
    orders = np.asarray(orders, float)
    g = np.asarray(guesses, float)
    if len(g) < 4 or len(np.unique(g[:, 0])) < 2:
        raise ValueError("identify at least four lines in at least two orders")
    all_x = np.concatenate([np.asarray(p, float) for p in peaks])
    all_m = np.concatenate([np.full(len(p), m) for p, m in zip(peaks, orders, strict=True)])
    if len(exclude):
        ex = np.asarray(exclude, float).reshape(-1, 2)
        drop = np.zeros(len(all_x), bool)
        for m, x in ex:
            drop |= (all_m == m) & (np.abs(all_x - x) < 1.5)
        all_x, all_m = all_x[~drop], all_m[~drop]
    nx = nx or (all_x.max() + 1)
    xs = (nx / 2, nx / 2)
    ms = (orders.mean(), max(np.ptp(orders) / 2, 1.0))

    # a catalogue line with a neighbour closer than twice the tolerance is ambiguous: a dense list (ThAr has a
    # line every ~2 A) otherwise lets wrong pairs into the fit, which then drifts by tenths of an Angstrom
    gap = np.minimum(np.diff(catalogue, prepend=-np.inf), np.diff(catalogue, append=np.inf))

    def match(sol, tol, window):
        pred = sol(all_x, all_m)
        idx = np.clip(np.searchsorted(catalogue, pred), 1, len(catalogue) - 1)
        near = np.where(np.abs(catalogue[idx - 1] - pred) < np.abs(catalogue[idx] - pred), idx - 1, idx)
        dist = np.abs(catalogue[near] - pred)
        ok = (dist < tol) & (gap[near] > 2 * tol) & window
        key = near * 10000 + all_m.astype(int)  # one peak per catalogue line and order: the closest
        for k in np.unique(key[ok]):
            same = ok & (key == k)
            if same.sum() > 1:
                ok[same] = False
                ok[np.where(same)[0][np.argmin(dist[same])]] = True
        return near, ok

    def fit(near, ok, dx, dm):
        if ok.sum() <= (dx + 1) * (dm + 1) + 2:
            raise ValueError("too few lines matched: check the identified lines, order numbers and line list")
        c, keep, sd = _fit_2d(all_x[ok], all_m[ok], all_m[ok] * catalogue[near[ok]], dx, dm, xs, ms, clip)
        return EchelleSolution(c, xs, ms, float(sd), int(keep.sum()), orders), keep, sd

    dx0 = int(min(2, deg_x, len(g) // 2 - 1))  # three lines spread along an order already fix a curve
    c, _, _ = _fit_2d(g[:, 1], g[:, 0], g[:, 0] * g[:, 2], max(dx0, 1), 1, xs, ms)
    sol = EchelleSolution(c, xs, ms, 0.0, len(g), orders)
    disp = abs(float(np.diff(sol(np.array([nx / 2, nx / 2 + 1]), orders.mean()))[0]))
    tol = 2 * disp
    # matching starts between the identified lines, where the first solution is good, and grows outwards: along
    # the orders and across them (a solution from three orders does not reach forty)
    lo, hi = g[:, 1].min(), g[:, 1].max()
    m_lo, m_hi = g[:, 0].min() - 1, g[:, 0].max() + 1
    while True:
        near, ok = match(sol, tol, (all_x >= lo) & (all_x <= hi) & (all_m >= m_lo) & (all_m <= m_hi))
        n_m = len(np.unique(all_m[ok]))
        dx = int(min(deg_x, max(1, ok.sum() // 10)))
        # few terms in m while few orders are matched: a cubic in m from a handful of orders runs off in the next
        dm = int(min(deg_m, n_m - 1, 1 if n_m < 12 else 2 if n_m < 25 else deg_m))
        sol, keep, sd = fit(near, ok, dx, dm)
        tol = min(tol, max(4 * sd, disp))  # tighter as the solution improves, never below a pixel
        if lo <= all_x.min() and hi >= all_x.max() and m_lo <= orders.min() and m_hi >= orders.max():
            break
        lo, hi = lo - 0.15 * nx, hi + 0.15 * nx
        m_lo, m_hi = m_lo - 1, m_hi + 1  # one order at a time: each new order is predicted from its neighbour
    everywhere = np.ones(len(all_x), bool)
    for _ in range(3):  # final passes over all lines with a tightened tolerance and the full degrees
        near, ok = match(sol, max(3 * sd, 0.3 * disp), everywhere)
        sol, keep, sd = fit(near, ok, deg_x, min(deg_m, len(orders) - 1))
    resid_all = catalogue[near[ok]] - sol(all_x[ok], all_m[ok])
    sol.rms = float(np.sqrt(np.mean(resid_all[keep] ** 2)))
    sol.lines = [
        [float(m), float(x), float(lam), float(r), bool(k)]
        for m, x, lam, r, k in zip(all_m[ok], all_x[ok], catalogue[near[ok]], resid_all, keep, strict=True)
    ]
    return sol


def scattered_light(image, coefs, step=16, deg=4, smooth=31):
    """2-D model of the light between the orders (see the module text). Needs gaps of 3 px or more."""
    from scipy.ndimage import uniform_filter1d

    img = np.asarray(image, float)
    ny, nx = img.shape
    cols = np.arange(step // 2, nx, step)
    yy = np.arange(ny)
    model_cols = np.zeros((ny, len(cols)))
    for j, x in enumerate(cols):
        centres = np.sort([np.polyval(c, x) for c in coefs])
        if len(centres) < 2:
            raise ValueError("at least two orders are needed to measure the scattered light")
        d = np.diff(centres)
        mids = np.r_[centres[0] - d[0] / 2, centres[:-1] + d / 2, centres[-1] + d[-1] / 2]
        spacing = np.r_[d[0], d, d[-1]]  # the gap between two orders is as wide as their distance
        keep = (mids > 1) & (mids < ny - 2) & (spacing >= 3)
        x0, x1 = max(0, x - step // 2), min(nx, x + step // 2 + 1)
        ys, vs = [], []
        for m in mids[keep]:
            r = int(round(m))
            vs.append(np.nanmedian(img[r - 1 : r + 2, x0:x1]))
            ys.append(m)
        ys, vs = np.asarray(ys), np.asarray(vs)
        if len(ys) < 3:
            continue
        use = np.isfinite(vs)
        u = (ys - ny / 2) / (ny / 2)
        k = min(deg, use.sum() - 2)
        for _ in range(4):  # a gap holding a cosmic ray or a stray line is clipped
            c = np.polyfit(u[use], vs[use], k)
            r = vs - np.polyval(c, u)
            sd = 1.4826 * np.median(np.abs(r[use] - np.median(r[use]))) or np.std(r[use])
            new = np.isfinite(vs) & (np.abs(r) < 3 * max(sd, 1e-9))
            if np.array_equal(new, use) or new.sum() < k + 2:
                break
            use = new
        model_cols[:, j] = np.polyval(c, (yy - ny / 2) / (ny / 2))
    model = np.array([np.interp(np.arange(nx), cols, row) for row in model_cols])
    return uniform_filter1d(model, size=max(1, smooth // step * step + 1), axis=1, mode="nearest")


def order_number(lam_a, lam_b):
    """Absolute order of the order with wavelength lam_a, given lam_b at the same pixel in the next
    order towards longer wavelength (m - 1). From the grating equation m lam_a = (m - 1) lam_b."""
    return lam_b / (lam_b - lam_a)


def merge(waves, fluxes, errors, blaze_fn=None, min_blaze=0.1, step=None):
    """One spectrum from all orders. Returns (wave, flux, error) on a log-lambda grid.

    Each order is divided by its blaze (pixels below min_blaze of the peak dropped), then
    resampled; overlapping orders are averaged with inverse-variance weights."""
    waves, fluxes, errors = (np.asarray(a, float) for a in (waves, fluxes, errors))
    if blaze_fn is None:
        blaze_fn = np.ones_like(fluxes)
    good = (blaze_fn >= min_blaze) & np.isfinite(fluxes) & (errors > 0)
    lw = np.log(waves)
    if step is None:
        step = np.nanmedian(np.abs(np.diff(lw, axis=1)))
    lo, hi = np.nanmin(np.where(good, lw, np.nan)), np.nanmax(np.where(good, lw, np.nan))
    grid = np.arange(lo, hi + step / 2, step)
    num, den = np.zeros(len(grid)), np.zeros(len(grid))
    for w, f, e, b, g in zip(lw, fluxes, errors, blaze_fn, good, strict=True):
        if g.sum() < 2:
            continue
        o = np.argsort(w[g])
        wo, fo, eo = w[g][o], (f[g] / b[g])[o], (e[g] / b[g])[o]
        inside = (grid >= wo[0]) & (grid <= wo[-1])
        fi = np.interp(grid[inside], wo, fo)
        vi = np.interp(grid[inside], wo, eo) ** 2
        num[inside] += fi / vi
        den[inside] += 1 / vi
    have = den > 0
    return np.exp(grid[have]), num[have] / den[have], 1 / np.sqrt(den[have])
