"""More charts of the Plan window, in a window of their own (UF-5: the airmass.org-style views) so the main chart
stays uncluttered: the Moon's distance from every target through the night, and the sky as seen at one hour (polar,
north up, east left) with a slider. The charts are in English (they go into papers and reports)."""

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QSlider, QTabWidget, QVBoxLayout, QWidget

from .kit.tokens import SERIES, role
from .kit.widgets import PlotCanvas
from .plan_chart import clock


def _name(t):
    return t["body"].capitalize() if t.get("body") else t["name"]


def draw_moon_distance(fig, n, hours, offset):
    """The Moon's angular distance from every target against the hour, where the Sun is below the horizon."""
    fig.clear()
    ax = fig.add_subplot()
    dark = np.asarray(n["sun_alt"], float) < -0.8
    for i, t in enumerate(n["targets"]):
        sep = np.where(dark, np.asarray(t["moon_sep"], float), np.nan)
        ax.plot(hours, sep, color=SERIES[i % len(SERIES)], lw=2, label=_name(t))
    ax.axhline(30, color=role("saturated"), lw=0.7, ls=":")
    ax.text(hours[0] + 0.1, 31, "30°: closer is usually too bright", fontsize=6, color=role("saturated"))
    ax.set_xlim(hours[0], hours[-1])
    ax.set_ylim(0, 180)
    ax.set_yticks(range(0, 181, 30))
    ticks = np.arange(np.ceil(hours[0]), hours[-1] + 0.01, 1.0)
    ax.set_xticks(ticks, [f"{int(h) % 24:02d}" for h in ticks], fontsize=7)
    ax.secondary_xaxis(-0.1, functions=(lambda h: h + offset, lambda h: h - offset)).set_xlabel(
        f"Local time (UTC{offset:+g})", fontsize=8
    )
    ax.grid(color=role("rejected"), alpha=0.3, lw=0.5)
    ax.set_xlabel("UTC (hours)", fontsize=8)
    ax.set_ylabel("Distance from the Moon (°)", fontsize=8)
    ax.set_title(f"Moon distance, {100 * n['moon_illumination']:.0f} % illuminated", fontsize=9)
    ax.legend(fontsize=7, loc="upper right")
    return ax


def draw_sky(fig, n, hours, k):
    """The sky at grid point k: polar, zenith at the centre, north up, east to the left (as the sky looks)."""
    fig.clear()
    ax = fig.add_subplot(projection="polar")
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(1)  # azimuth grows counter-clockwise: east on the left, the way the sky looks overhead
    ax.set_rlim(90, 0)  # the centre is the zenith
    ax.set_rgrids([0, 30, 60], labels=["", "60°", "30°"], fontsize=7)
    ax.set_thetagrids(range(0, 360, 45), ["N", "NE", "E", "SE", "S", "SW", "W", "NW"], fontsize=8)
    for i, t in enumerate(n["targets"]):
        az, alt = np.radians(t["az"][k]), t["alt"][k]
        colour = SERIES[i % len(SERIES)]
        ax.plot(np.radians(t["az"]), t["alt"], color=colour, lw=0.6, alpha=0.35)  # the night's track
        if alt > 0:
            ax.plot([az], [alt], "o", color=colour, ms=8, label=f"{_name(t)}  {alt:.0f}°")
    if n["moon_alt"][k] > 0:
        ax.plot([np.radians(n["moon_az"][k])], [n["moon_alt"][k]], "o", mfc="none", mec=role("rejected"), ms=12,
                label=f"Moon  {n['moon_alt'][k]:.0f}°")  # fmt: skip
    ax.set_title(f"Sky at {clock(hours[k])} UTC   (Sun {n['sun_alt'][k]:.0f}°)", fontsize=9, pad=14)
    ax.legend(fontsize=7, loc="upper left", bbox_to_anchor=(1.02, 1.0))
    return ax


class MoreCharts(QDialog):
    def __init__(self, n, hours, offset, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("More charts of the night"))
        self.n, self.hours, self.offset = n, np.asarray(hours, float), offset
        tabs = QTabWidget(self)
        self.moon = PlotCanvas(self)
        draw_moon_distance(self.moon.figure, n, self.hours, offset)
        tabs.addTab(self.moon, self.tr("Moon distance"))
        sky = QWidget(self)
        lay = QVBoxLayout(sky)
        self.sky = PlotCanvas(self)
        lay.addWidget(self.sky, 1)
        row = QHBoxLayout()
        self.when = QLabel(sky)
        self.slider = QSlider(Qt.Horizontal, sky)
        self.slider.setRange(0, len(self.hours) - 1)
        # open at the middle of the astronomical night, or of the grid when there is none
        dark = np.flatnonzero(np.asarray(n["sun_alt"]) < -18)
        self.slider.setValue(int(dark[len(dark) // 2]) if len(dark) else len(self.hours) // 2)
        self.slider.valueChanged.connect(self._sky)
        row.addWidget(QLabel(self.tr("Hour"), sky))
        row.addWidget(self.slider, 1)
        row.addWidget(self.when)
        lay.addLayout(row)
        tabs.addTab(sky, self.tr("Sky at an hour"))
        QVBoxLayout(self).addWidget(tabs)
        self.resize(760, 560)
        self._sky(self.slider.value())

    def _sky(self, k):
        draw_sky(self.sky.figure, self.n, self.hours, k)
        self.sky.draw()
        self.when.setText(f"{clock(self.hours[k])} UTC / {clock(self.hours[k] + self.offset)}")
