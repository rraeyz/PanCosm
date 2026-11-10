"""What a figure shows, as plain data: the interactive view (view.py) and the publication output (publish.py) draw
the same description, so a printed figure always matches the screen (plans/architecture.md ARC-6).

    spec = FigureSpec([PanelSpec(AxisSpec("BJD", time="bjd"), AxisSpec("Δmag", invert=True),
                                 [SeriesSpec("V", t, mag, yerr=err)])])

No Qt here. Arrays stay NumPy arrays; to_dict() turns them into lists for JSON.
"""

from dataclasses import asdict, dataclass, field

import numpy as np

KINDS = ("points", "line", "steps", "errorbars", "band", "vline", "hline", "histogram")
# Okabe & Ito (2008) colour-blind-safe palette, in the order series take them
OKABE_ITO = ("#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#F0E442", "#000000")
MAX_POINTS = 50_000  # per series in view; above this the view decimates
MAX_ERRORBARS = 5_000  # error bars are drawn only below this many points in view


@dataclass
class AxisSpec:
    label: str = ""
    unit: str = ""
    scale: str = "linear"  # or "log"
    invert: bool = False
    time: str | None = None  # None, "bjd", "phase" or "ut"
    limits: tuple | None = None  # (low, high), None = fit the data
    period: float | None = None  # with epoch, a time axis can also be shown as phase
    epoch: float = 0.0

    def title(self, offset=0.0):
        """Axis title with the unit and, for times, the offset subtracted from the numbers."""
        text = self.label
        if offset:
            text += f" − {offset:.10g}"
        return f"{text} [{self.unit}]" if self.unit else text


@dataclass
class SeriesSpec:
    name: str
    x: np.ndarray
    y: np.ndarray | None = None
    yerr: np.ndarray | None = None
    xerr: np.ndarray | None = None
    kind: str = "points"
    colour: str | None = None  # None = next colour of OKABE_ITO
    symbol: str = "o"
    size: float = 4.0
    width: float = 1.0
    alpha: float = 1.0
    z: int = 0
    pickable: bool = False
    ids: np.ndarray | None = None  # what point_clicked reports; default: the index
    visible: bool = True

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ValueError(f"unknown series kind {self.kind}")
        for name in ("x", "y", "yerr", "xerr", "ids"):
            value = getattr(self, name)
            if value is not None:
                setattr(self, name, np.asarray(value))


@dataclass
class PanelSpec:
    x: AxisSpec
    y: AxisSpec
    series: list = field(default_factory=list)
    height_ratio: float = 1.0
    grid: bool = False


@dataclass
class FigureSpec:
    panels: list
    shared_x: bool = True
    title: str = ""

    def colours(self):
        """{series name: colour}, giving the palette's colours in order to series without one."""
        out, free = {}, iter(OKABE_ITO * 8)
        for panel in self.panels:
            for s in panel.series:
                if s.name not in out:
                    out[s.name] = s.colour or next(free)
        return out

    def to_dict(self):
        def plain(v):
            if isinstance(v, np.ndarray):
                return v.tolist()
            if isinstance(v, dict):
                return {k: plain(x) for k, x in v.items()}
            if isinstance(v, list | tuple):
                return [plain(x) for x in v]
            return v

        return plain(asdict(self))


def in_time_mode(figure, mode):
    """A copy of the figure whose time axes ("bjd") show `mode`: "bjd" (unchanged), "ut" (UT hours, 0-24, from the
    Julian date; shortcut: BJD taken as UT, off by up to 8.3 min, fine for reading the night's hours) or "phase"
    (needs the axis' period). Axes without a period keep their times when phase is asked."""
    from copy import deepcopy

    out = deepcopy(figure)
    for panel in out.panels:
        axis = panel.x
        if axis.time != "bjd" or mode == "bjd" or (mode == "phase" and not axis.period):
            continue
        for s in panel.series:
            if s.kind == "hline":
                continue
            if mode == "ut":
                s.x = ((s.x - 0.5) % 1.0) * 24.0
            else:
                s.x = ((s.x - axis.epoch) / axis.period) % 1.0
        axis.label, axis.unit, axis.time = ("UT", "h", "ut") if mode == "ut" else ("phase", "", "phase")
        axis.limits = None
    return out


def time_offset(values, axis):
    """A round number to subtract from time axes so that their labels stay short (BJD 2460512.3 → 512.3)."""
    if axis.time not in ("bjd", "jd", "mjd") or values is None or not len(values):
        return 0.0
    low = float(np.nanmin(values))
    return float(np.floor(low / 1000) * 1000) if abs(low) >= 10_000 else 0.0


def decimate_line(x, y, x0, x1, columns):
    """The points of a line inside [x0, x1], reduced to the minimum and maximum per pixel column when there are more
    than MAX_POINTS: peaks stay visible, and the result is exact once zoomed in far enough. x must be sorted."""
    i0, i1 = np.searchsorted(x, [x0, x1])
    i0, i1 = max(i0 - 1, 0), min(i1 + 1, len(x))  # one point outside on each side, so the line reaches the edges
    xs, ys = x[i0:i1], y[i0:i1]
    if len(xs) <= MAX_POINTS:
        return xs, ys
    edges = np.unique(np.searchsorted(xs, np.linspace(xs[0], xs[-1], columns + 1)[:-1]))
    bounds = list(zip(edges, [*edges[1:], len(ys)], strict=True))
    arg_lo = edges + np.array([np.argmin(ys[a:b]) for a, b in bounds])
    arg_hi = edges + np.array([np.argmax(ys[a:b]) for a, b in bounds])
    order = np.sort(np.column_stack([arg_lo, arg_hi]), axis=1).ravel()  # min and max in the order they occur
    return xs[order], ys[order]


def decimate_points(x, y, x0, x1, y0, y1, width, height):
    """Indices of the points inside the view, one per occupied pixel cell when there are more than MAX_POINTS: a
    scatter plot looks the same, and the nearest-point read-out still finds real points."""
    inside = np.flatnonzero((x >= x0) & (x <= x1) & (y >= y0) & (y <= y1))
    if len(inside) <= MAX_POINTS:
        return inside
    cx = ((x[inside] - x0) / ((x1 - x0) or 1) * (width - 1)).astype(np.int64)
    cy = ((y[inside] - y0) / ((y1 - y0) or 1) * (height - 1)).astype(np.int64)
    _, first = np.unique(cx * height + cy, return_index=True)
    return inside[np.sort(first)]
