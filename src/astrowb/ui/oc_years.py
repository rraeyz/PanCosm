"""A year axis for the O-C diagram: round years placed at their epochs E = (JD - T0) / P."""

import numpy as np
from astropy.time import Time

from .plot.spec import AxisSpec

STEPS = (1, 2, 5, 10, 20, 50, 100)
FULL_JD = 2_000_000  # below this the times are reduced (JD - offset), not full JDs


def year_ticks(t0, period, e_min, e_max):
    """[(epoch, "year")] at round years over the epoch range; [] if T0 is not a full JD or there is no range."""
    if t0 < FULL_JD or period <= 0 or not e_max > e_min:
        return []
    y0, y1 = Time([t0 + e_min * period, t0 + e_max * period], format="jd").decimalyear
    step = next((s for s in STEPS if (y1 - y0) / s <= 8), STEPS[-1])
    years = np.arange(np.ceil(y0 / step) * step, y1 + 1e-9, step).astype(int)
    if len(years) < 3 and step > 1:  # a coarse step can leave fewer than 3 ticks: take the next finer one
        step = STEPS[STEPS.index(step) - 1]
        years = np.arange(np.ceil(y0 / step) * step, y1 + 1e-9, step).astype(int)
    jds = Time([f"{y:04d}-01-01" for y in years], scale="utc").jd if len(years) else []
    return [(float((jd - t0) / period), str(y)) for jd, y in zip(jds, years, strict=True)]


def year_axis(t0, period, epochs, label):
    """The panel's `top` AxisSpec, or None."""
    ticks = year_ticks(t0, period, float(np.min(epochs)), float(np.max(epochs)))
    return AxisSpec(label, ticks=ticks) if ticks else None
