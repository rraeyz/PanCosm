"""The Plan window's night, Moon-distance and year charts as FigureSpecs (ARC-6): PlotView shows them, publish.py
prints them. The charts are in English (they go into papers and reports)."""

import numpy as np

from .kit.tokens import SERIES, role
from .plan_chart import AIRMASS_TICKS, EDGES, SHADES, altitude_of, clock, crossing_hours
from .plot.spec import AxisSpec, FigureSpec, PanelSpec, SeriesSpec


def name_of(t):
    return t["body"].capitalize() if t.get("body") else t["name"]


def dark_spans(hours, sun, level):
    """[(from hour, to hour)] where the Sun is below `level`, one per stretch."""
    below = np.concatenate([[False], np.asarray(sun) < level, [False]])
    edges = np.flatnonzero(below[1:] != below[:-1])
    return [(float(hours[i]), float(hours[j - 1])) for i, j in zip(edges[::2], edges[1::2], strict=True)]


def _sidereal(n, hours):
    """h -> local sidereal time (hours) at the site, or None when the night has no site longitude."""
    lon = (n.get("site") or {}).get("lon")
    if lon is None:
        return None
    from astropy.time import Time

    lst0 = float(Time(n["jd"][0], format="jd").sidereal_time("mean", longitude=f"{lon}d").hour)
    return lambda h: lst0 + (h - hours[0]) * 1.00273791


def _hour_axes(hours, offset, lst=None):
    """UTC along the bottom (a tick every hour) and the local time (over the sidereal time, when given) along the
    top, both on the same positions."""
    ticks = [(float(h), f"{int(h) % 24:02d}") for h in np.arange(np.ceil(hours[0]), hours[-1] + 0.01, 1.0)]
    local = [(k - offset, f"{k % 24:02d}") for k in range(int(np.ceil(hours[0] + offset)), int(hours[-1] + offset) + 1)]
    local = [(float(v), t) for v, t in local if hours[0] <= v <= hours[-1]]
    if lst:
        local = [(v, f"{t}\n{int(round(lst(v))) % 24:02d}h") for v, t in local]
    x = AxisSpec("UTC (hours)", limits=(hours[0], hours[-1]), ticks=ticks)
    label = f"Local time (UTC{offset:+g})" + (" / sidereal time" if lst else "")
    return x, AxisSpec(label, ticks=local)


def _twilight(hours, sun):
    """The shaded bands, the dashed edges and their written times."""
    out = []
    for level, shade in SHADES:
        spans = dark_spans(hours, sun, level)
        if spans:
            out.append(
                SeriesSpec(f"Sun below {level:g}°", *np.array(spans).T, kind="span", colour=SERIES[0], alpha=shade)
            )
    edges, labels = [], []
    for name, level in EDGES:
        down, up = crossing_hours(hours, sun, level)
        for h, tag in [*[(x, "dusk") for x in down], *[(x, "dawn") for x in up]]:
            label = "Sunset" if name == "sunset" and tag == "dusk" else "Sunrise" if name == "sunset" else name[:5]
            edges.append(h)
            labels.append(f"{label} {clock(h)}")
    if edges:
        out.append(SeriesSpec("Twilight edges", edges, kind="vline", colour=role("rejected"), dash="dash"))
        out.append(SeriesSpec("Twilight times", edges, [84.0] * len(edges), kind="text", labels=labels, angle=90,
                              colour=role("rejected")))  # fmt: skip
    return out


def _target_series(n, hours, sun, min_alt):
    out, events = [], []
    for i, t in enumerate(n["targets"]):
        colour = SERIES[i % len(SERIES)]
        alt = np.asarray(t["alt"], float)
        floor = np.asarray(t.get("limit") or np.full(len(alt), min_alt), float)  # the horizon profile, when given
        down, up = crossing_hours(hours, alt - floor, 0.0)
        rise = clock(up[0]) if up else ("up" if alt[0] >= floor[0] else "—")
        set_ = clock(down[-1]) if down else ("up" if alt[-1] >= floor[-1] else "—")
        name = f"{name_of(t)}   ↑ {rise}  ↓ {set_}"
        out.append(
            SeriesSpec(name, hours, np.where(alt >= floor, alt, np.nan), kind="line", colour=colour, width=2.2, z=4)
        )
        out.append(SeriesSpec(name, hours, alt, kind="line", colour=colour, alpha=0.55, z=3))  # thin below the limit
        sep = t.get("moon_sep")
        if sep is not None:  # the Moon's distance from the target, along its curve every hour
            xs, ys, txt = [], [], []
            for h in np.arange(np.ceil(hours[0]), np.floor(hours[-1]) + 0.01, 1.0):
                k = int(np.argmin(np.abs(hours - h)))
                if alt[k] >= max(min_alt, 5) and sun[k] < -0.8:
                    xs.append(h), ys.append(alt[k] + 5.0), txt.append(f"{sep[k]:.0f}°")
            if xs:
                out.append(
                    SeriesSpec(f"{name_of(t)}: Moon distance", xs, ys, kind="text", labels=txt, colour=colour, z=5)
                )
        events += [(e, t) for e in t["events"]]
    if events:
        mid = np.floor(n["jd"][0] + 0.5) - 0.5
        sig = np.array([(e.get("sigma_min") or 0) / 60 for e, _ in events])  # how well its time is known (PLN-4): ±1σ
        out.append(SeriesSpec("Events", [(e["mid"] - mid) * 24 for e, _ in events], [e["alt_mid"] for e, _ in events],
                              xerr=sig, symbol="v", size=9, colour=role("saturated"), z=6))  # fmt: skip
    return out


def night_figure(n, hours, offset, min_alt):
    """The night n (planning.night's result): altitude against UTC (local time on top), the twilights shaded, every
    target thick above its limit and thin below, the Moon dashed. hours: the grid in UTC hours; offset: local − UTC."""
    hours, sun = np.asarray(hours, float), np.asarray(n["sun_alt"], float)
    series = _twilight(hours, sun) + _target_series(n, hours, sun, min_alt)
    if not any(t.get("body") == "moon" for t in n["targets"]):
        series.append(SeriesSpec(f"Moon ({100 * n['moon_illumination']:.0f} %)", hours, n["moon_alt"], kind="line",
                                 colour=role("rejected"), dash="dash", width=1.5, z=2))  # fmt: skip
    series += [SeriesSpec("Altitude limit", [min_alt], kind="hline", colour=role("saturated"), dash="dot"),
               SeriesSpec("Limit label", [hours[0] + 0.1], [min_alt + 0.8], kind="text", labels=[f"limit {min_alt:g}°"],
                          colour=role("saturated"))]  # fmt: skip
    x, top = _hour_axes(hours, offset, _sidereal(n, hours))
    y = AxisSpec("Altitude (°)", limits=(0, 90), ticks=[(v, str(v)) for v in range(0, 91, 10)])
    right = AxisSpec("Airmass", ticks=[(float(altitude_of(a)), f"{a:g}") for a in AIRMASS_TICKS])
    site = n.get("site") or {}
    where = ""
    if site.get("lon") is not None:
        ew, ns = ("E" if site["lon"] >= 0 else "W"), ("N" if site["lat"] >= 0 else "S")
        where = f"{abs(site['lon']):.4f}°{ew}  {abs(site['lat']):.4f}°{ns}  {site.get('height', 0):.0f} m"
    title = f"{site.get('name') or 'Site'}   {where}   night of {n.get('date', '')}"
    return FigureSpec([PanelSpec(x, y, series, grid=True, top=top, right=right)], title=title)


def moon_figure(n, hours, offset):
    """The Moon's angular distance from every target against the hour, where the Sun is below the horizon."""
    hours = np.asarray(hours, float)
    dark = np.asarray(n["sun_alt"], float) < -0.8
    series = [SeriesSpec(name_of(t), hours, np.where(dark, np.asarray(t["moon_sep"], float), np.nan), kind="line",
                         colour=SERIES[i % len(SERIES)], width=2) for i, t in enumerate(n["targets"])]  # fmt: skip
    series += [SeriesSpec("30°", [30.0], kind="hline", colour=role("saturated"), dash="dot"),
               SeriesSpec("30° label", [hours[0] + 0.1], [31.0], kind="text",
                          labels=["30°: closer is usually too bright"],
                          colour=role("saturated"))]  # fmt: skip
    x, top = _hour_axes(hours, offset)
    y = AxisSpec("Distance from the Moon (°)", limits=(0, 180), ticks=[(v, str(v)) for v in range(0, 181, 30)])
    title = f"Moon distance, {100 * n['moon_illumination']:.0f} % illuminated"
    return FigureSpec([PanelSpec(x, y, series, grid=True, top=top)], title=title)


def year_figure(dates, hours, sun, chosen):
    """The nights of a year: date across, local solar time (noon … noon) up, one band per twilight level (stacked, so
    darker as the Sun goes down) between its first and last dark hour; the chosen night marked. Local solar time
    follows the site's longitude (no zone, no summer time)."""
    d = np.array(dates, dtype="datetime64[D]")
    x = (d - d[0]).astype(float)
    sun, hours = np.asarray(sun, float), np.asarray(hours, float)
    series = []
    for level, _shade in SHADES:
        mid, half = np.full(len(x), np.nan), np.full(len(x), np.nan)
        for i, row in enumerate(sun):
            dark = np.flatnonzero(row < level)
            if len(dark):
                mid[i], half[i] = 12 + (hours[dark[0]] + hours[dark[-1]]) / 2, (hours[dark[-1]] - hours[dark[0]]) / 2
        series.append(SeriesSpec(f"Sun below {level:g}°", x, mid, yerr=half, kind="band", colour=SERIES[0]))
    series.append(SeriesSpec("Chosen night", [float((np.datetime64(chosen, "D") - d[0]).astype(float))], kind="vline",
                             colour=role("saturated")))  # fmt: skip
    months = [(float((m - d[0]).astype(float)), str(m.astype("datetime64[M]").astype(object).strftime("%b")))
              for m in np.unique(d.astype("datetime64[M]")).astype("datetime64[D]") if m >= d[0]]  # fmt: skip
    xa = AxisSpec("Date", ticks=months, limits=(0.0, float(x[-1])))
    ya = AxisSpec("Local solar time (h)", limits=(12, 36), ticks=[(h, f"{h % 24:02d}") for h in range(12, 37, 2)])
    title = "Night length through the year (dark blue: astronomical night; lighter: nautical, civil twilight)"
    return FigureSpec([PanelSpec(xa, ya, series, grid=True)], title=title)
