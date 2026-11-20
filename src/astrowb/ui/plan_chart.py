"""The night chart's helpers (the chart itself: plan_figures.py; user-feedback UF-1 … UF-5): an observer's chart,
drawn from the planning step's result — the altitude of every target and the Moon through the night with

- the time axis in UTC with a tick every hour and a minor tick every 10 minutes, the local time as a second row
  under it, the local sidereal time along the top (as the ING "staralt" chart);
- altitude labelled every 10° (minor 5°), the airmass on the right (1.0 … 5), a grid on the major and the minor ticks;
- the twilights as bands (sunset–civil, nautical, astronomical, night: the blue gradient), their edges dashed with
  their UTC times written;
- every target's curve, thick where it is above the altitude limit, thin below; the Moon's distance from each target
  written along its curve every hour; the events marked; the Moon dashed with its illumination;
- the legend with each target's rise and set through the altitude limit; the site and the date in the title.
The chart is in English whatever the interface language: it goes into papers and reports.
"""

import numpy as np

EDGES = (("sunset", 0.0), ("civil", -6.0), ("nautical", -12.0), ("astronomical", -18.0))
SHADES = ((0.0, 0.07), (-6.0, 0.14), (-12.0, 0.22), (-18.0, 0.32))  # darker as the Sun goes down
AIRMASS_TICKS = (1.0, 1.1, 1.2, 1.3, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0)


def airmass_of(alt):
    with np.errstate(divide="ignore", invalid="ignore"):
        return 1 / np.sin(np.radians(np.clip(alt, 1, 90)))


def altitude_of(x):
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.degrees(np.arcsin(1 / np.clip(x, 1, 60)))


def crossing_hours(hours, values, level):
    """The hours where values cross level: ([falling], [rising]), linear between the grid's points."""
    v = np.asarray(values, float) - level
    down, up = [], []
    for i in np.flatnonzero(np.sign(v[:-1]) != np.sign(v[1:])):
        h = hours[i] + (hours[i + 1] - hours[i]) * v[i] / (v[i] - v[i + 1])
        (down if v[i] > 0 else up).append(float(h))
    return down, up


def clock(h):
    h = h % 24
    m = int(round((h - int(h)) * 60))
    return f"{int(h) + m // 60:02d}:{m % 60:02d}" if int(h) + m // 60 < 24 else "00:00"
