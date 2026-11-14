"""More charts of the Plan window, in a window of their own (UF-5: the airmass.org-style views) so the main chart
stays uncluttered: the Moon's distance from every target through the night, and the sky as seen at one hour (polar,
north up, east left) with a slider. The charts are in English (they go into papers and reports)."""

import numpy as np
from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QSlider, QTabWidget, QVBoxLayout, QWidget

from .kit.tokens import SERIES, role
from .kit.widgets import PlotCanvas
from .plan_chart import SHADES, clock


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
    moon_az, moon_alt = np.asarray(n["moon_az"], float), np.asarray(n["moon_alt"], float)
    up = np.where(moon_alt > 0, moon_alt, np.nan)  # the Moon's track while it is above the horizon
    ax.plot(np.radians(moon_az), up, "--", color=role("rejected"), lw=0.8)
    lit = f"{100 * n['moon_illumination']:.0f} %"
    if moon_alt[k] > 0:
        ax.plot([np.radians(moon_az[k])], [moon_alt[k]], "o", mfc="none", mec=role("rejected"), ms=14, mew=2,
                label=f"Moon ({lit})  {moon_alt[k]:.0f}°")  # fmt: skip
    else:
        ax.plot([], [], "o", mfc="none", mec=role("rejected"), label=f"Moon ({lit}) below the horizon")
    ax.set_title(f"Sky at {clock(hours[k])} UTC   (Sun {n['sun_alt'][k]:.0f}°)", fontsize=9, pad=14)
    ax.legend(fontsize=7, loc="upper left", bbox_to_anchor=(1.02, 1.0))
    return ax


def draw_year(fig, dates, hours, sun, chosen):
    """The nights of a year: date across, local solar time (noon … noon) up, the twilights shaded as in the night
    chart; the chosen night marked. Local solar time follows the site's longitude (no zone, no summer time)."""
    import matplotlib.dates as mdates

    fig.clear()
    ax = fig.add_subplot()
    x = mdates.date2num(np.array(dates, dtype="datetime64[D]").astype(object))
    for level, shade in SHADES:  # darker as the Sun goes down, as in the night chart
        ax.contourf(x, 12 + hours, np.asarray(sun).T, levels=[-90, level], colors="navy", alpha=shade)
    ax.axvline(mdates.date2num(np.datetime64(chosen, "D").astype(object)), color=role("saturated"), lw=1)
    ax.set_yticks(range(12, 37, 2), [f"{h % 24:02d}" for h in range(12, 37, 2)], fontsize=7)
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.grid(color=role("rejected"), alpha=0.3, lw=0.5)
    ax.set_ylabel("Local solar time (h)", fontsize=8)
    ax.set_title("Night length through the year (dark blue: astronomical night; lighter: nautical, civil twilight)",
                 fontsize=9)  # fmt: skip
    return ax


def draw_weather(fig, f, hours0_jd, sun_hours=None, sun_alt=None):
    """Cloud cover (total, low, middle, high) and humidity through the forecast hours, in UTC hours of the night's
    grid (hours0_jd: the JD of its 00:00 UTC); the night shaded when the Sun's altitude is given."""
    fig.clear()
    ax = fig.add_subplot()
    h = (np.asarray(f["time"], float) - hours0_jd) * 24
    if sun_hours is not None:
        for level, shade in SHADES:
            ax.fill_between(sun_hours, 0, 100, where=np.asarray(sun_alt) < level, color="navy", alpha=shade, lw=0)
    for key, label, colour, width in (
        ("cloud", "total", role("rejected"), 2.4),
        ("cloud_low", "low", SERIES[0], 1.2),
        ("cloud_mid", "middle", SERIES[1], 1.2),
        ("cloud_high", "high", SERIES[2], 1.2),
    ):
        ax.plot(h, f[key], color=colour, lw=width, label=f"Cloud {label} (%)")  # fmt: skip
    ax.plot(h, f["humidity"], ":", color=SERIES[5], lw=1.2, label="Humidity (%)")
    ax.set_ylim(0, 100)
    ax.set_xlim(sun_hours[0], sun_hours[-1]) if sun_hours is not None else None
    ax.set_xlabel("UTC (hours)", fontsize=8)
    ax.set_ylabel("%", fontsize=8)
    ax.grid(color=role("rejected"), alpha=0.3, lw=0.5)
    ax.legend(fontsize=7, loc="upper right")
    ax.set_title(f"Forecast — {f['source']}", fontsize=8)
    return ax


class _Relay(QObject):
    done = Signal(object)


class MoreCharts(QDialog):
    def __init__(self, n, hours, offset, parent=None, min_alt=20.0):
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
        self.year = PlotCanvas(self)
        tabs.addTab(self.year, self.tr("Through the year"))
        tabs.currentChanged.connect(lambda i: i == 2 and self._year())  # computed when first looked at
        from PySide6.QtWidgets import QPushButton, QScrollArea

        weather = QWidget(self)
        wl = QVBoxLayout(weather)
        self.weather_button = QPushButton(self.tr("Get the forecast"), weather)
        self.weather_button.setToolTip(self.tr("Cloud cover, humidity and wind for the site from Open-Meteo "
                                               "(needs the internet; kept for an hour)"))  # fmt: skip
        self.weather_button.clicked.connect(self.fetch_weather)
        self.weather_note = QLabel(weather)
        self.weather_note.setWordWrap(True)
        self.weather = PlotCanvas(self)
        wl.addWidget(self.weather_button)
        wl.addWidget(self.weather_note)
        wl.addWidget(self.weather, 1)
        tabs.addTab(weather, self.tr("Weather"))

        from .plan_tables import tables_page

        self.tables = tables_page(n, self.hours, offset, min_alt)
        scroll = QScrollArea(self)
        scroll.setWidget(self.tables)
        scroll.setWidgetResizable(True)
        tabs.addTab(scroll, self.tr("Tables"))
        QVBoxLayout(self).addWidget(tabs)
        self.resize(760, 560)
        self._sky(self.slider.value())

    def _sky(self, k):
        draw_sky(self.sky.figure, self.n, self.hours, k)
        self.sky.draw()
        self.when.setText(f"{clock(self.hours[k])} UTC / {clock(self.hours[k] + self.offset)}")

    def _year(self):
        if self.year.figure.axes:
            return
        from ..planning.visibility import Site, year_nights

        site, date = self.n["site"], self.n["date"]
        dates, h, sun = year_nights(Site(site["name"], site["lat"], site["lon"], site["height"]), date)
        draw_year(self.year.figure, dates, h, sun, date)
        self.year.draw()

    def fetch_weather(self, fetch=None):
        """The forecast looked up off the window's thread (PLN-11); fetch: for tests."""
        import threading

        site = self.n["site"]
        self.weather_note.setText(self.tr("Asking Open-Meteo…"))
        self.relay = _Relay(self)
        self.relay.done.connect(self.show_weather)

        def work():
            from ..services import forecast

            try:
                answer = forecast.forecast(site["lat"], site["lon"], fetch=fetch)
            except Exception as e:  # noqa: BLE001 - the network or the service: said in the window
                answer = e
            try:
                self.relay.done.emit(answer)
            except RuntimeError:  # the window was closed meanwhile
                pass

        threading.Thread(target=work, daemon=True).start()

    def show_weather(self, answer):
        from .messages import translate

        if isinstance(answer, Exception):
            self.weather_note.setText(translate(answer))
            return
        zero = float(np.floor(self.n["jd"][0] + 0.5) - 0.5)
        draw_weather(self.weather.figure, answer, zero, self.hours, self.n["sun_alt"])
        self.weather.draw()
        from astropy.time import Time

        issued = Time(answer["issued"], format="jd").iso[:16] if answer.get("issued") else "—"
        self.weather_note.setText(
            self.tr("Forecast fetched {when} UTC. {source}").format(when=issued, source=answer["source"])
        )
