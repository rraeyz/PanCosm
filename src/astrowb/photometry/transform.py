"""Transformed (standard-system) magnitudes on every frame (plans/photometry.md PHO-35).

With the AAVSO convention of photometry/coefficients.py, (V − v) = T_v (B − V) + Z_v: a star's standard magnitude is
its instrumental one plus the frame's zero point plus the colour term. In ensemble photometry the comparison stars
give the zero point, so

    V_target = −2.5 log10(F_t / Σ F_c) + m_ens(V_c − T_v (B−V)_c) + T_v (B−V)_target

i.e. the ensemble magnitude computed with each comparison star's catalogue magnitude moved off its colour term,
plus the target's colour term. The target's colour comes from the night's other filter (interpolated in time and
iterated, as the transformed magnitudes change it) or is typed. The error adds the coefficient's error times the
target's colour distance from the comparison stars.
"""

import numpy as np

from .export import ensemble_magnitudes


def transformed(lc, comp_mags, comp_colours, target_colour, coefficient, coefficient_error=0.0):
    """(magnitudes, errors) per frame in the standard system. target_colour: one value or one per frame."""
    comp_mags, comp_colours = np.asarray(comp_mags, float), np.asarray(comp_colours, float)
    colour = np.asarray(target_colour, float)
    mag, err = ensemble_magnitudes(lc, comp_mags - coefficient * comp_colours)
    mag = mag + coefficient * colour
    err = np.hypot(err, coefficient_error * np.abs(colour - np.nanmean(comp_colours)))
    return mag, err


def transformed_pair(lc_a, lc_b, mags_a, mags_b, t_a, t_b, errors=(0.0, 0.0), iterations=6):
    """Both filters of a night transformed together (e.g. A = B, B = V): each frame's target colour (A − B) from the
    other filter's transformed curve interpolated to its time, iterated. mags_a / mags_b: the comparison stars'
    catalogue magnitudes in A and B; t_a / t_b: the magnitude coefficients T_a, T_b (on A − B).
    Returns {"a": (mag, err), "b": (mag, err), "colour_a": per A frame, "colour_b": per B frame}."""
    mags_a, mags_b = np.asarray(mags_a, float), np.asarray(mags_b, float)
    comp_colour = mags_a - mags_b
    time_a, time_b = np.asarray(lc_a["jd_utc"], float), np.asarray(lc_b["jd_utc"], float)
    a0, _ = ensemble_magnitudes(lc_a, mags_a)  # untransformed: the first colour
    b0, _ = ensemble_magnitudes(lc_b, mags_b)
    colour_a = a0 - _follow(time_a, time_b, b0)
    colour_b = _follow(time_b, time_a, a0) - b0
    for _ in range(iterations):
        a = transformed(lc_a, mags_a, comp_colour, colour_a, t_a, errors[0])
        b = transformed(lc_b, mags_b, comp_colour, colour_b, t_b, errors[1])
        colour_a = a[0] - _follow(time_a, time_b, b[0])
        colour_b = _follow(time_b, time_a, a[0]) - b[0]
    return {"a": a, "b": b, "colour_a": colour_a, "colour_b": colour_b}


def _follow(t, t_other, values):
    """The other filter's curve at the times t (linear between its frames, held at the ends)."""
    ok = np.isfinite(values) & np.isfinite(t_other)
    order = np.argsort(t_other[ok])
    return np.interp(t, t_other[ok][order], np.asarray(values)[ok][order])
