"""UF-1 … UF-5: the Plan window's night chart is an observer's chart — hourly and ten-minute ticks, 10° / 5° altitude
ticks, a grid, the twilights with their times, the local time under UTC and the sidereal time on top, the airmass
on the right, the Moon's distance along each curve, rise and set in the legend, the site and date in the title."""

import numpy as np
import pytest

from astrowb.engine.steps import execute
from astrowb.ui.plan_chart import crossing_hours
from astrowb.ui.plan_figures import night_figure
from astrowb.ui.plot import publish

SITE = {"name": "TUBITAK National Observatory", "lat": 36.8242, "lon": 30.3356, "height": 2500.0}


class Ctx:
    def progress(self, *a):
        pass

    def check(self):
        pass


def night():
    targets = [{"name": "Saturn", "ra": 0, "dec": 0}, {"name": "HAT-P-32 b", "ra": 31.04, "dec": 46.69,
               "t0": 2455867.4027, "period": 2.15, "duration": 0.13}]  # fmt: skip
    return execute(
        "planning.night",
        {"site": SITE, "date": "2026-11-13", "targets": targets},
        {"min_alt": 20.0, "step_min": 5.0},
        Ctx(),
    )["night"]


def test_the_chart_has_what_an_astronomer_reads():
    n = night()
    jd = np.asarray(n["jd"])
    hours = (jd - (np.floor(jd[0] + 0.5) - 0.5)) * 24
    spec = night_figure(n, hours, 3.0, 20.0)
    (panel,) = spec.panels
    assert np.allclose(np.diff([v for v, _ in panel.x.ticks]), 1.0)  # a tick every hour
    assert (
        panel.top.label.startswith("Local time (UTC+3")
        and panel.top.ticks[0][1].split("\n")[0] == f"{int(np.ceil(hours[0] + 3)) % 24:02d}"
    )
    assert np.allclose(np.diff([v for v, _ in panel.y.ticks]), 10) and panel.y.limits == (0, 90)
    assert "TUBITAK National Observatory" in spec.title and "2026-11-13" in spec.title
    names = [s.name for s in panel.series]
    assert any(t.startswith("Saturn   ↑") for t in names) and any(t.startswith("Moon (") for t in names)
    kinds = {s.name: s.kind for s in panel.series}
    assert "span" in kinds.values() and kinds["Twilight edges"] == "vline" and kinds["Events"] == "points"
    texts = [t for s in panel.series if s.kind == "text" for t in s.labels]
    assert any(t.startswith("astro") for t in texts) and any(t.startswith("Sunset") for t in texts)
    assert any(t.endswith("°") and t[:-1].isdigit() for t in texts)  # the Moon's distance along a curve
    assert "\n" in panel.top.ticks[0][1] and "sidereal" in panel.top.label  # local time over sidereal time
    assert panel.right.label == "Airmass" and panel.right.ticks[0] == (90.0, "1")  # altitude 90° is airmass 1
    publish.figure(spec).canvas.draw()  # and the same description prints


def test_crossings_and_twilight_bands():
    h = np.linspace(0, 10, 101)
    down, up = crossing_hours(h, np.cos(h * np.pi / 5), 0.0)
    assert np.allclose(down, [2.5], atol=0.01) and np.allclose(up, [7.5], atol=0.01)


def test_more_charts(qapp):
    from astrowb.ui.plan_more import MoreCharts

    n = night()
    hours = (np.asarray(n["jd"]) - (np.floor(n["jd"][0] + 0.5) - 0.5)) * 24
    win = MoreCharts(n, hours, 3.0)
    assert "Moon distance" in win.moon.figure.title and win.moon.figure.panels[0].top is not None
    win.slider.setValue(10)
    assert win.sky.figure.axes[0].get_title().startswith("Sky at")
    assert len(win.sky.figure.axes[0].lines) >= len(n["targets"])


def test_auto_local_time_follows_the_site(qapp, tmp_path):
    from astrowb.settings import Settings
    from astrowb.ui.plan_page import AUTO, PlanPage

    page = PlanPage(Settings(tmp_path))
    page.utc_offset.setValue(AUTO)
    page.lon.setValue(-120.0)  # nowhere near any computer's zone that is within 2 h of it... unless it is Pacific
    assert abs(page.local_offset(2461000.0) - (-8)) <= 1


def test_year_chart(qapp):
    from astrowb.ui.plan_more import MoreCharts

    n = night()
    hours = (np.asarray(n["jd"]) - (np.floor(n["jd"][0] + 0.5) - 0.5)) * 24
    win = MoreCharts(n, hours, 3.0)
    win._year()
    spec = win.year.figure
    panel = spec.panels[0]
    assert "Night length" in spec.title and panel.y.limits[1] >= 36 and len(panel.x.ticks) >= 11
    night_band = next(s for s in panel.series if s.name == "Sun below -18°")
    assert np.isfinite(night_band.y).any()


def test_the_night_in_numbers():
    from astrowb.ui.plan_tables import moon_rows, standard_rows, sun_rows, target_rows

    n = night()
    hours = (np.asarray(n["jd"]) - (np.floor(n["jd"][0] + 0.5) - 0.5)) * 24
    sun = sun_rows(n, hours, 3.0)
    assert [r[0] for r in sun][:2] == ["Sunset", "Civil dusk (−6°)"] and sun[-1][0] == "Sunrise"
    assert sun[0][1] == "14:46" and sun[0][2] == "17:46"  # as the chart writes it (UTC) and in local time
    assert {r[0] for r in moon_rows(n, hours, 3.0)} >= {"Moonrise", "Moonset", "Illuminated"}
    saturn, hat = target_rows(n, hours, 3.0, 20.0)
    assert saturn[0] == "Saturn" and saturn[1] == "17:41" and saturn[2] == "02:24"  # the legend's 14:41 / 23:24 UTC
    assert float(saturn[5]) == pytest.approx(1 / np.sin(np.radians(float(saturn[4][:-1]))), abs=0.02)
    assert hat[0] == "HAT-P-32 b" and hat[6].endswith("°")
    (std,) = standard_rows(n, hours, 3.0)  # Saturn has no fixed place: only HAT-P-32 b gets a telluric standard
    assert std[0] == "HAT-P-32 b" and std[1].startswith("HIP ") and abs(float(std[3]) - float(std[4])) <= 0.1
    (lan,) = standard_rows(n, hours, 3.0, "landolt1992")  # a Landolt standard at the same airmass (PLN-9)
    assert lan[0] == "HAT-P-32 b" and lan[1] != "—" and abs(float(lan[3]) - float(lan[4])) <= 0.1


def test_the_weather_tab(qtbot):
    from test_forecast import ANSWER

    from astrowb.ui.plan_more import MoreCharts

    n = night()
    hours = (np.asarray(n["jd"]) - (np.floor(n["jd"][0] + 0.5) - 0.5)) * 24
    win = MoreCharts(n, hours, 3.0)
    qtbot.addWidget(win)
    win.fetch_weather(fetch=lambda url: ANSWER)
    qtbot.waitUntil(lambda: win.weather.figure is not None, timeout=20000)
    spec = win.weather.figure
    kinds = {s.name: s.kind for s in spec.panels[0].series}
    assert "Open-Meteo" in spec.title and "Open-Meteo" in win.weather_note.text()
    assert kinds["Humidity (%)"] == "line" and kinds["Cloud total (%)"] == "line"
    assert "span" in kinds.values()  # the night shaded as bands behind the curves


def test_almanac_line_follows_the_site_and_date(qtbot, tmp_path):
    """UI-16.8 stage 1: the night's almanac in local time under the site, refreshed when the date changes."""
    from PySide6.QtCore import QDate

    from astrowb.planning.night import summary
    from astrowb.planning.visibility import Site
    from astrowb.settings import Settings
    from astrowb.ui.plan_chart import clock
    from astrowb.ui.plan_page import PlanPage

    page = PlanPage(Settings(tmp_path))
    qtbot.addWidget(page)
    qtbot.waitUntil(lambda: bool(page.almanac.text()), timeout=5000)
    assert page.almanac.text().startswith("No site saved yet")  # PLN-W: a new user is told first
    page.site_name.setText("Ankara")
    page.lat.setValue(39.84)
    page.lon.setValue(32.78)
    page.height.setValue(1250)
    page.utc_offset.setValue(3.0)
    page.date.setDate(QDate(2026, 11, 14))
    qtbot.waitUntil(lambda: page.almanac.text().startswith("Sunset"), timeout=5000)
    qtbot.waitUntil(lambda: not page._almanac_timer.isActive(), timeout=5000)
    a = summary(Site("", 39.84, 32.78, 1250), "2026-11-14", step_min=1.0)
    text = page.almanac.text()
    assert (
        text.startswith(f"Sunset {clock(a['sun_down'] + 3)}")
        and f"({a['astronomical_up'] - a['astronomical_down']:.1f} h)" in text
    )
    assert "% lit" in text
    page.date.setDate(QDate(2026, 6, 21))
    qtbot.waitUntil(lambda: page.almanac.text() != text, timeout=5000)


def test_year_bands_cover_exactly_the_hours_of_their_level_and_nest():
    from astrowb.ui.plan_figures import year_figure

    hours = np.linspace(0, 24, 97)  # noon to noon
    dates = [f"2026-01-{d:02d}" for d in range(1, 11)]
    depth = np.linspace(-25, -5, len(dates))[:, None]  # the Sun's lowest altitude each night
    sun = depth * np.cos(2 * np.pi * (hours - 12) / 24 + np.pi)[None, :] * -1 - 3  # lowest at 12 h after noon
    spec = year_figure(dates, hours, sun, "2026-01-05")
    bands = [s for s in spec.panels[0].series if s.kind == "band"]
    last = None
    for s, level in zip(bands, (0.0, -6.0, -12.0, -18.0), strict=True):
        for i, row in enumerate(sun):
            dark = np.flatnonzero(row < level)
            if not len(dark):
                assert np.isnan(s.y[i])
                continue
            lo, hi = 12 + s.y[i] - 12 - s.yerr[i], 12 + s.y[i] - 12 + s.yerr[i]
            assert (lo, hi) == pytest.approx((12 + hours[dark[0]], 12 + hours[dark[-1]]))
            if last is not None and np.isfinite(last[0][i]):
                assert last[0][i] - last[1][i] <= lo + 1e-9 and hi <= last[0][i] + last[1][i] + 1e-9  # nested
        last = (s.y, s.yerr)
