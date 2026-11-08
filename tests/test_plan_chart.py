"""UF-1 … UF-5: the Plan window's night chart is an observer's chart — hourly and ten-minute ticks, 10° / 5° altitude
ticks, a grid, the twilights with their times, the local time under UTC and the sidereal time on top, the airmass
on the right, the Moon's distance along each curve, rise and set in the legend, the site and date in the title."""

import numpy as np
import pytest
from matplotlib.figure import Figure

from astrowb.engine.steps import execute
from astrowb.ui.plan_chart import crossing_hours, draw_night

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
    fig = Figure(figsize=(14, 7), layout="constrained")
    ax = draw_night(fig, n, hours, 3.0, 20.0, 1400)
    fig.canvas.draw()
    major = [t for t in ax.get_xticks() if hours[0] <= t <= hours[-1]]
    assert np.allclose(np.diff(major), 1.0)  # a tick every hour
    minor = ax.xaxis.get_minorticklocs()
    assert np.isclose(np.min(np.diff(minor)), 1 / 6)  # every ten minutes between
    assert np.allclose(np.diff(ax.get_yticks()), 10) and 5.0 in ax.yaxis.get_minorticklocs()
    assert ax.xaxis.get_major_ticks()[1].gridline.get_visible() and ax.xaxis.get_minor_ticks()[1].gridline.get_visible()
    every = [ax, *ax.child_axes]
    labels = [a.get_xlabel() for a in every] + [a.get_ylabel() for a in every]
    tags = [t.get_text() for t in every[0].texts]
    assert "◄ UTC" in tags and any(x.startswith("◄ Local (UTC+3") for x in tags)
    assert "Local sidereal time" in labels and "Airmass" in labels
    assert "TUBITAK National Observatory" in ax.get_title() and "2026-11-13" in ax.get_title()
    legend = " ".join(t.get_text() for t in ax.get_legend().get_texts())
    assert "Saturn   ↑" in legend and "Moon (" in legend
    texts = [t.get_text() for t in ax.texts]
    assert any(t.startswith("astro") for t in texts) and any(t.startswith("Sunset") for t in texts)
    assert any(t.endswith("°") and t[:-1].isdigit() for t in texts)  # the Moon's distance along a curve


def test_crossings_and_twilight_bands():
    h = np.linspace(0, 10, 101)
    down, up = crossing_hours(h, np.cos(h * np.pi / 5), 0.0)
    assert np.allclose(down, [2.5], atol=0.01) and np.allclose(up, [7.5], atol=0.01)


def test_more_charts(qapp):
    from astrowb.ui.plan_more import MoreCharts

    n = night()
    hours = (np.asarray(n["jd"]) - (np.floor(n["jd"][0] + 0.5) - 0.5)) * 24
    win = MoreCharts(n, hours, 3.0)
    assert "Moon distance" in win.moon.figure.axes[0].get_title()
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
    ax = win.year.figure.axes[0]
    assert "Night length" in ax.get_title() and ax.get_ylim()[1] >= 36


def test_the_night_in_numbers():
    from astrowb.ui.plan_tables import moon_rows, sun_rows, target_rows

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
