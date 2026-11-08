"""The night chart of the Plan window (user-feedback UF-1 … UF-5): an observer's chart, drawn from the planning
step's result — the altitude of every target and the Moon through the night with

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
from matplotlib.ticker import FixedLocator, MultipleLocator

from .kit.tokens import SERIES, role

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


def _hour_labels(axis, step):
    axis.set_major_locator(MultipleLocator(step))
    axis.set_minor_locator(MultipleLocator(1 / 6))
    axis.set_major_formatter(lambda h, _p: f"{int(round(h)) % 24:02d}")
    axis.set_tick_params(which="major", length=6, labelsize=8)
    axis.set_tick_params(which="minor", length=3)


def draw_night(fig, n, hours, offset, min_alt, width_px=1200):
    """Draw the night n (planning.night's result) on the figure; hours: the grid in UTC hours from 00:00 UTC of its
    first date; offset: local time − UTC in hours; min_alt: the lowest altitude that counts."""
    fig.clear()
    ax = fig.add_subplot()
    sun = np.asarray(n["sun_alt"], float)
    _twilight(ax, hours, sun)
    _targets(ax, n, hours, sun, min_alt)
    _axes(ax, n, hours, offset, min_alt, 1 if width_px >= 900 else 2, fig.get_figheight() * fig.dpi)
    return ax


def _twilight(ax, hours, sun):
    for level, shade in SHADES:
        ax.fill_between(hours, 0, 90, where=(sun < level), color="navy", alpha=shade, lw=0, zorder=0)
    ax.set_facecolor("none")

    top = 90.0
    for name, level in EDGES:  # the twilights' edges, dashed, with their UTC times
        down, up = crossing_hours(hours, sun, level)
        for h, tag in [*[(x, "dusk") for x in down], *[(x, "dawn") for x in up]]:
            ax.axvline(h, color=role("rejected"), lw=0.7, ls="--", zorder=1)
            label = "Sunset" if name == "sunset" and tag == "dusk" else "Sunrise" if name == "sunset" else name[:5]
            ax.text(h, top - 0.8, f"{label} {clock(h)}", rotation=90, ha="right", va="top", fontsize=6,
                    color=role("rejected"), clip_on=True)  # fmt: skip


def _targets(ax, n, hours, sun, min_alt):
    for i, t in enumerate(n["targets"]):
        colour = SERIES[i % len(SERIES)]
        alt = np.asarray(t["alt"], float)
        name = t["body"].capitalize() if t.get("body") else t["name"]
        above = np.where(alt >= min_alt, alt, np.nan)
        ax.plot(hours, alt, color=colour, lw=0.9, alpha=0.55, zorder=3)
        down, up = crossing_hours(hours, alt, min_alt)
        rise = clock(up[0]) if up else ("up" if alt[0] >= min_alt else "—")
        set_ = clock(down[-1]) if down else ("up" if alt[-1] >= min_alt else "—")
        ax.plot(hours, above, color=colour, lw=2.2, zorder=4, label=f"{name}   ↑ {rise}  ↓ {set_}")
        sep = t.get("moon_sep")
        if sep is not None:  # the Moon's distance from the target, along its curve every hour
            sep = np.asarray(sep, float)
            for h in np.arange(np.ceil(hours[0]), np.floor(hours[-1]) + 0.01, 1.0):
                k = int(np.argmin(np.abs(hours - h)))
                if alt[k] >= max(min_alt, 5) and sun[k] < -0.8:
                    ax.text(h, alt[k] + 1.8, f"{sep[k]:.0f}°", color=colour, fontsize=6, ha="center",
                            va="bottom", clip_on=True, zorder=5)  # fmt: skip
        for e in t["events"]:
            h = (e["mid"] - np.floor(n["jd"][0] + 0.5) + 0.5) * 24
            ax.plot([h], [e["alt_mid"]], "v", color=role("saturated"), ms=7, zorder=6)
    if not any(t.get("body") == "moon" for t in n["targets"]):
        ax.plot(hours, n["moon_alt"], "--", color=role("rejected"), lw=1.1, zorder=2,
                label=f"Moon ({100 * n['moon_illumination']:.0f} %)")  # fmt: skip

    ax.axhline(min_alt, color=role("saturated"), lw=0.7, ls=":", zorder=2)
    ax.text(hours[0] + 0.1, min_alt + 0.8, f"limit {min_alt:g}°", fontsize=6, color=role("saturated"))
    ax.legend(fontsize=7, loc="center left", bbox_to_anchor=(1.075, 0.5), framealpha=0.9)  # beside the airmass scale


def _axes(ax, n, hours, offset, min_alt, step, fig_px):
    """Hourly major, ten-minute minor ticks, a grid on both; the local time, the sidereal time, the airmass."""
    ax.set_xlim(hours[0], hours[-1])
    ax.set_ylim(0, 90)
    _hour_labels(ax.xaxis, step)
    ax.yaxis.set_major_locator(MultipleLocator(10))
    ax.yaxis.set_minor_locator(MultipleLocator(5))
    ax.tick_params(axis="y", which="major", labelsize=8)
    ax.grid(which="major", color=role("rejected"), alpha=0.35, lw=0.6)
    ax.grid(which="minor", color=role("rejected"), alpha=0.15, lw=0.4)
    ax.set_xlabel("UTC (hours)", fontsize=8)
    ax.set_ylabel("Altitude (°)", fontsize=8)

    height_px = max(200.0, fig_px * 0.55)  # the plot's share of the figure: the local row sits ~42 px below it
    local = ax.secondary_xaxis(-42.0 / height_px, functions=(lambda h: h + offset, lambda h: h - offset))
    _hour_labels(local.xaxis, step)
    local.set_xlabel(f"Local time (UTC{offset:+g})", fontsize=8)

    site = n.get("site") or {}
    lon = site.get("lon")
    if lon is not None:
        from astropy.time import Time

        lst0 = float(Time(n["jd"][0], format="jd").sidereal_time("mean", longitude=f"{lon}d").hour)
        sidereal = ax.secondary_xaxis("top", functions=(lambda h: lst0 + (h - hours[0]) * 1.00273791,
                                                        lambda s: hours[0] + (s - lst0) / 1.00273791))  # fmt: skip
        sidereal.xaxis.set_major_locator(MultipleLocator(step))
        sidereal.xaxis.set_major_formatter(lambda s, _p: f"{int(round(s)) % 24:02d}h")
        sidereal.set_xlabel("Local sidereal time", fontsize=8)
        sidereal.tick_params(labelsize=8)

    air = ax.secondary_yaxis("right", functions=(airmass_of, altitude_of))
    air.yaxis.set_major_locator(FixedLocator(AIRMASS_TICKS))
    air.yaxis.set_major_formatter(lambda x, _p: f"{x:g}")
    air.set_ylabel("Airmass", fontsize=8)
    air.tick_params(labelsize=8)

    place = site.get("name") or "Site"
    where = ""
    if lon is not None:
        ew, ns = ("E" if lon >= 0 else "W"), ("N" if site["lat"] >= 0 else "S")
        where = f"{abs(lon):.4f}°{ew}  {abs(site['lat']):.4f}°{ns}  {site.get('height', 0):.0f} m"
    ax.set_title(f"{place}   {where}   night of {n.get('date', '')}", fontsize=9)
