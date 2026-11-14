"""The almanac line under the Plan window's site and date (plans/interface.md UI-16.8 stage 1, planning/night.summary):
sunset, the dark hours, sunrise and the Moon of the chosen night in local time, refreshed as the site or date
changes."""

from PySide6.QtCore import QCoreApplication, QTimer
from PySide6.QtWidgets import QLabel

from .plan_chart import clock

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("Ctx", "…") calls


def text(a, offset):
    """One line from night.summary()'s dict, times shifted by offset hours (UTC → local)."""

    def at(h):
        return "—" if h is None else clock(h + offset)

    parts = [translate("PlanAlmanac", "Sunset {t}").format(t=at(a["sun_down"]))]
    down, up = a["astronomical_down"], a["astronomical_up"]
    if down is not None and up is not None:
        line = translate("PlanAlmanac", "dark {start}–{end} ({hours:.1f} h)")
        parts.append(line.format(start=at(down), end=at(up), hours=up - down))
    else:
        parts.append(translate("PlanAlmanac", "no astronomical darkness"))
    parts.append(translate("PlanAlmanac", "sunrise {t}").format(t=at(a["sun_up"])))
    parts.append(translate("PlanAlmanac", "Moon {pct:.0f} % lit, rises {rise}, sets {set}").format(
        pct=100 * a["moon_illumination"], rise=at(a["moon_rise"]), set=at(a["moon_set"])))  # fmt: skip
    return " · ".join(parts)


def almanac_label(page):
    """The label, refreshed 0.3 s after the last change of the site, the date or the local-time offset."""
    label = QLabel(page)
    label.setWordWrap(True)
    label.setToolTip(translate("PlanAlmanac", "The chosen night at this site, in local time; dark: the Sun below −18°"))
    timer = QTimer(page)
    timer.setSingleShot(True)
    timer.setInterval(300)
    timer.timeout.connect(lambda: refresh(page, label))
    for w in (page.lat, page.lon, page.height, page.utc_offset):
        w.valueChanged.connect(timer.start)
    page.date.dateChanged.connect(timer.start)
    page.almanac, page._almanac_timer = label, timer
    timer.start()
    return label


def refresh(page, label):
    from astropy.time import Time

    from ..planning.night import summary
    from ..planning.visibility import Site

    date = page.date.date().toString("yyyy-MM-dd")
    site = Site("", page.lat.value(), page.lon.value(), page.height.value())
    a = summary(site, date, step_min=10.0)  # the crossings are interpolated: within a second of a fine grid
    label.setText(text(a, page.local_offset(Time(f"{date}T00:00:00").jd + 1.0)))
    return a
