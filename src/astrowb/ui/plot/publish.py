"""The publication figure of a FigureSpec, drawn with Matplotlib, plus the numbers behind it and a script that redraws
it (ARC-6 item 5). The same spec as the screen, so limits, series and labels match what the user saw.

    publish(spec, "lc.pdf", style="aas", width="single")
    data_behind(spec, "lc.ecsv"); script(spec, "lc.py", "lc.ecsv")
"""

import datetime
from pathlib import Path

import numpy as np
from matplotlib.figure import Figure

from ... import __version__
from . import spec as S

# column widths in inches and sizes per journal (AAS: 3.5 / 7.1 in; A&A: 88 / 180 mm; MNRAS: 84 / 174 mm)
STYLES = {
    "aas": {"single": 3.5, "double": 7.1, "font": 8, "line": 0.8, "marker": 2.0},
    "aanda": {"single": 3.46, "double": 7.09, "font": 8, "line": 0.8, "marker": 2.0},
    "mnras": {"single": 3.31, "double": 6.85, "font": 8, "line": 0.8, "marker": 2.0},
    "screen": {"single": 6.0, "double": 10.0, "font": 11, "line": 1.2, "marker": 3.0},
}
RASTER_ABOVE = 20_000  # points of one series; more are rasterised inside the vector file (journals' size limits)
_MARKERS = {"o": "o", "s": "s", "^": "^", "v": "v", "d": "D", "+": "+", "x": "x", "*": "*"}


def figure(spec, style="aas", width="single"):
    """A Matplotlib Figure of the spec (not shown anywhere)."""
    st = STYLES[style]
    w = st[width]
    ratios = [p.height_ratio for p in spec.panels]
    h = w * 0.62 * (sum(ratios) / max(ratios[0], 1e-9)) ** 0.5 if len(ratios) > 1 else w * 0.62
    rc = {"font.size": st["font"], "font.family": "STIXGeneral", "mathtext.fontset": "stix"}
    import matplotlib

    with matplotlib.rc_context(rc):
        fig = Figure(figsize=(w, h), layout="constrained")
        axes = fig.subplots(len(spec.panels), 1, sharex=spec.shared_x, squeeze=False, height_ratios=ratios)[:, 0]
        colours = spec.colours()
        for ax, panel in zip(axes, spec.panels, strict=True):
            _panel(ax, panel, colours, st)
        if spec.title:
            axes[0].set_title(spec.title)
        if spec.shared_x:
            for ax in axes[:-1]:
                ax.set_xlabel("")
    return fig


def _panel(ax, panel, colours, st):
    xs = [s.x for s in panel.series if s.kind not in ("hline",)]
    offset = S.time_offset(np.concatenate(xs) if xs else None, panel.x)
    for s in panel.series:
        if not s.visible:
            continue
        c, x = colours[s.name], (s.x - offset if s.kind != "hline" else s.x)
        kw = {"color": c, "alpha": s.alpha, "zorder": s.z + 2, "label": s.name}
        many = s.y is not None and len(s.x) > RASTER_ABOVE
        if s.kind in ("points", "errorbars"):
            size = st["marker"] * s.size / 4
            if s.yerr is not None or s.xerr is not None:
                ax.errorbar(x, s.y, yerr=s.yerr, xerr=s.xerr, fmt="none", ecolor=c, elinewidth=st["line"] * 0.5,
                            alpha=s.alpha, zorder=s.z + 1, rasterized=many)  # fmt: skip
            ax.plot(x, s.y, ls="none", marker=_MARKERS.get(s.symbol, "o"), ms=size, mew=0, rasterized=many, **kw)
        elif s.kind in ("line", "steps"):
            ax.plot(x, s.y, lw=st["line"] * s.width, drawstyle="steps-post" if s.kind == "steps" else "default",
                    rasterized=many, **kw)  # fmt: skip
        elif s.kind == "histogram":
            ax.stairs(s.y, s.x - offset, fill=True, **kw)
        elif s.kind == "band":
            ax.fill_between(x, s.y - s.yerr, s.y + s.yerr, lw=0, **{**kw, "alpha": 0.25 * s.alpha})
        elif s.kind == "vline":
            for v in x:
                ax.axvline(v, lw=st["line"] * s.width, **{**kw, "label": None})
        elif s.kind == "hline":
            for v in s.x:
                ax.axhline(v, lw=st["line"] * s.width, **{**kw, "label": None})
    ax.set_xlabel(panel.x.title(offset))
    ax.set_ylabel(panel.y.title())
    ax.set_xscale(panel.x.scale)
    ax.set_yscale(panel.y.scale)
    if panel.x.limits:
        ax.set_xlim(panel.x.limits[0] - offset, panel.x.limits[1] - offset)
    if panel.y.limits:
        ax.set_ylim(*panel.y.limits)
    if panel.x.invert:
        ax.invert_xaxis()
    if panel.y.invert:
        ax.invert_yaxis()
    ax.tick_params(direction="in", top=True, right=True, which="both", width=st["line"] * 0.8)
    ax.minorticks_on()
    if panel.grid:
        ax.grid(alpha=0.3, lw=st["line"] * 0.5)
    if sum(1 for s in panel.series if s.visible and s.kind not in ("vline", "hline")) > 1:
        ax.legend(frameon=False)


def publish(spec, path, style="aas", width="single", dpi=600):
    """Write the figure: PDF, EPS, SVG (fonts embedded as TrueType) or PNG at dpi. Returns the path."""
    from ...brand import load

    path = Path(path)
    import matplotlib

    with matplotlib.rc_context({"pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "path"}):
        fig = figure(spec, style, width)
        meta = {"Title": spec.title or path.stem, "Creator": f"{load().display_name} {__version__}"}
        if path.suffix.lower() == ".pdf":
            meta["CreationDate"] = datetime.datetime.now(datetime.UTC)
        elif path.suffix.lower() == ".png":
            meta = {"Title": meta["Title"], "Software": meta["Creator"]}
        elif path.suffix.lower() in (".eps", ".ps"):
            meta = {"Creator": meta["Creator"]}
        fig.savefig(path, dpi=dpi, metadata=meta)
    return path


def data_behind(spec, path):
    """The plotted numbers as an ECSV table: one row per point, the series and panel named in columns."""
    from astropy.table import Table

    rows = {"panel": [], "series": [], "x": [], "y": [], "yerr": [], "xerr": []}
    for i, panel in enumerate(spec.panels):
        for s in panel.series:
            n = len(s.x)
            rows["panel"] += [i] * n
            rows["series"] += [s.name] * n
            rows["x"] += list(s.x)
            for key in ("y", "yerr", "xerr"):
                v = getattr(s, key)
                rows[key] += list(v) if v is not None and len(v) == n else [np.nan] * n
    table = Table(rows)
    table.meta = {"figure": spec.title, "axes": [[p.x.title(), p.y.title()] for p in spec.panels]}
    table.write(path, format="ascii.ecsv", overwrite=True)
    return Path(path)


def script(spec, path, data_file):
    """A stand-alone Python script that redraws the figure from data_behind's ECSV (Matplotlib and Astropy only)."""
    lines = [
        '"""Redraws the figure from the numbers in the ECSV file next to this script."""',
        "import matplotlib.pyplot as plt",
        "from astropy.table import Table",
        "",
        f"t = Table.read({Path(data_file).name!r}, format='ascii.ecsv')",
        f"fig, axes = plt.subplots({len(spec.panels)}, 1, sharex={spec.shared_x}, squeeze=False,"
        f" figsize=(3.5, {2.2 * len(spec.panels):.1f}))",
    ]
    colours = spec.colours()
    for i, panel in enumerate(spec.panels):
        lines.append(f"ax = axes[{i}, 0]")
        for s in panel.series:
            sel = f"t[(t['panel'] == {i}) & (t['series'] == {s.name!r})]"
            style = "'-'" if s.kind in ("line", "steps") else "'o', ms=2"
            lines.append(f"d = {sel}")
            if s.kind in ("vline", "hline"):
                fn = "axvline" if s.kind == "vline" else "axhline"
                lines.append(f"for v in d['x']: ax.{fn}(v, color={colours[s.name]!r})")
            elif s.yerr is not None and s.kind not in ("band", "line"):
                lines.append(f"ax.errorbar(d['x'], d['y'], yerr=d['yerr'], fmt='o', ms=2, color={colours[s.name]!r},"
                             f" label={s.name!r})")  # fmt: skip
            else:
                lines.append(f"ax.plot(d['x'], d['y'], {style}, color={colours[s.name]!r}, label={s.name!r})")
        lines += [f"ax.set_xlabel({panel.x.title()!r})", f"ax.set_ylabel({panel.y.title()!r})"]
        if panel.y.invert:
            lines.append("ax.invert_yaxis()")
    lines += ["fig.tight_layout()", f"fig.savefig({Path(path).with_suffix('.pdf').name!r})", ""]
    Path(path).write_text("\n".join(lines), encoding="utf-8")
    return Path(path)
