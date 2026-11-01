"""Many minima from long or sparse series, by a template of the star's own eclipse (plans/oc.md OC-3; Zasche et al.
2014: a template fitted to chunks of data; Gies et al. 2012, Conroy et al. 2014: one template per star for Kepler).

    minima = eclipse_times(t, flux, t0, period)                  # dense data (TESS, Kepler): one time per eclipse
    minima = chunk_times(t, flux, t0, period)                    # sparse surveys: one time per chunk and kind

The template is the folded curve around each kind of minimum, its binned median smoothed; an eclipse is timed by
shifting the template, scaling its depth and fitting a straight baseline under it (least squares; the error from the
fit's covariance scaled by χ²ᵣ). Dense data are timed twice: the template is rebuilt from the curve folded on the
first pass's own times, so a varying period does not blur it. Returns [(time, error, kind)] like
minima.each_minimum.
"""

import numpy as np

from .minima import _smooth


def template_from_fold(t, y, t0, period, kind="I", half_width=0.08, times=None, bins=None):
    """(x, flux): the eclipse of this kind as a function of the time from its mid-point (days), from every cycle;
    with `times` (the mid-points of the eclipses, one per cycle), each cycle is folded on its own time."""
    t, y = np.asarray(t, float), np.asarray(y, float)
    shift = 0.0 if kind == "I" else 0.5
    if times is None:
        x = ((t - t0) / period - shift + 0.5) % 1.0 - 0.5
        x *= period
    else:
        times = np.sort(np.asarray(times, float))
        k = np.clip(np.searchsorted(times, t), 1, len(times) - 1)
        nearest = np.where(np.abs(t - times[k - 1]) < np.abs(t - times[k]), times[k - 1], times[k])
        x = t - nearest
    sel = np.abs(x) <= half_width * period
    x, yy = x[sel], y[sel]
    n = bins or int(np.clip(np.sqrt(sel.sum()) * 2, 30, 400))
    edges = np.linspace(-half_width * period, half_width * period, n + 1)
    which = np.digitize(x, edges) - 1
    centres, values = [], []
    for b in range(n):
        inside = yy[which == b]
        if inside.size >= 2:
            centres.append(0.5 * (edges[b] + edges[b + 1]))
            values.append(np.median(inside))
    if len(centres) < 10:
        raise ValueError("too few points around this kind of minimum to make its template")
    return np.array(centres), _smooth(np.array(values), 3)


def time_by_template(t, y, template, guess, err=None):
    """(time, error) of one eclipse: the template shifted by δ, its depth scaled by s, over a straight baseline
    a + b (t − guess). Raises ValueError when the fit does not converge or lands outside the window."""
    from scipy.optimize import least_squares

    x0, f0 = template
    top = float(np.median(np.r_[f0[: len(f0) // 6], f0[-len(f0) // 6 :]]))
    t, y = np.asarray(t, float), np.asarray(y, float)
    u = t - guess
    w = np.ones_like(y) if err is None else 1 / np.asarray(err, float)

    def model(p):
        d, s, a, b = p
        shape = np.interp(u - d, x0, f0, left=top, right=top) - top
        return a + b * u + s * shape

    span = x0[-1] - x0[0]
    res = least_squares(lambda p: (model(p) - y) * w, [0.0, 1.0, top, 0.0], x_scale="jac",
                        bounds=([-span / 4, 0.1, -np.inf, -np.inf], [span / 4, 10, np.inf, np.inf]))  # fmt: skip
    if not res.success or abs(res.x[0]) >= span / 4 * 0.999:
        raise ValueError("the template does not match this eclipse")
    dof = max(1, len(y) - 4)
    cov = np.linalg.pinv(res.jac.T @ res.jac) * float(np.sum(res.fun**2)) / dof
    return guess + float(res.x[0]), float(np.sqrt(max(cov[0, 0], 0.0)))


def _each(t, y, t0, period, templates, window):
    """Every eclipse each_minimum finds, timed by the template of its kind."""
    from .minima import each_minimum

    def timer(tw, yw):
        centre = 0.5 * (tw[0] + tw[-1])
        kind = "II" if abs((centre - t0) / period % 1.0 - 0.5) < 0.25 else "I"
        if kind not in templates:
            raise ValueError("no template for this kind of minimum")
        shift = 0.5 if kind == "II" else 0.0
        guess = t0 + (round((centre - t0) / period - shift) + shift) * period
        return time_by_template(tw, yw, templates[kind], guess)

    return each_minimum(t, y, t0, period, timer, window)[0]


def eclipse_times(t, y, t0, period, window=0.08, kinds=("I", "II")):
    """Dense data: one time per eclipse covered on both sides, by the star's own template, built again from the
    first pass's times. Returns [(time, error, kind)]."""
    t, y = np.asarray(t, float), np.asarray(y, float)
    order = np.argsort(t)
    t, y = t[order], y[order] / np.median(y)
    templates = {}
    for kind in kinds:
        try:
            templates[kind] = template_from_fold(t, y, t0, period, kind, window)
        except ValueError:
            continue
    first = _each(t, y, t0, period, templates, window)
    for kind in list(templates):
        times = [tm for tm, _e, k in first if k == kind]
        if len(times) >= 3:
            shift = 0.0 if kind == "I" else 0.5
            templates[kind] = template_from_fold(t, y, t0 + shift * period, period, "I", window, times=times)
    return _each(t, y, t0, period, templates, window)


def chunk_times(t, y, t0, period, window=0.08, kinds=("I", "II"), min_points=10):
    """Sparse data: for each kind, the points within `window` × period of an eclipse are taken in time order and cut
    into chunks of `min_points` (the last chunk keeps the remainder when it has at least half that); each chunk's
    points are moved to its middle cycle and the template's shift fitted, giving one time per chunk and kind."""
    t, y = np.asarray(t, float), np.asarray(y, float)
    order = np.argsort(t)
    t, y = t[order], y[order] / np.median(y)
    out = []
    for kind in kinds:
        shift = 0.0 if kind == "I" else 0.5
        try:
            template = template_from_fold(t, y, t0, period, kind, window)
        except ValueError:
            continue
        cycles = np.round((t - t0) / period - shift)
        x = t - (t0 + (cycles + shift) * period)
        near = np.flatnonzero(np.abs(x) <= window * period)
        groups = [near[i : i + min_points] for i in range(0, len(near), min_points)]
        if len(groups) > 1 and len(groups[-1]) < min_points // 2:
            groups[-2] = np.r_[groups[-2], groups.pop()]
        for g in groups:
            if len(g) < min_points // 2:
                continue
            middle = float(np.round(np.median(cycles[g])))
            centre = t0 + (middle + shift) * period
            try:  # the chunk's eclipses as one, at its middle cycle
                tm, e = time_by_template(centre + x[g], y[g], template, centre)
            except ValueError:
                continue
            out.append((tm, e, kind))
    return sorted(out)
