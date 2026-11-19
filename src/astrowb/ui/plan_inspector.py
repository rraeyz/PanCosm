"""The Planning window's inspector (plans/interface.md UI-16.8): the target chosen in the targets table, with what the
row and tonight's computed night already hold (coordinates, ephemeris and its σ, the night's events, when it is above
the limit, the Moon's distance). Nothing is computed here but a lookup and the span above the limit. Left out: the
field view with the sensor footprint, the exposure calculator and the last observation."""

import numpy as np
from astropy.time import Time
from PySide6.QtCore import QCoreApplication

from ..planning.events import ephemeris_errors
from .kit.inspector import Inspector
from .plan_page import _uncertainty

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("PlanWindow", "…") calls


def _sexagesimal(value, hours):
    """'13 38 48.1' (hours) or '−02 01 49' (degrees) of a number of degrees."""
    sign = "−" if value < 0 else ""
    value = abs(value) / 15 if hours else abs(value)
    h = int(value)
    m = int((value - h) * 60)
    s = ((value - h) * 60 - m) * 60
    if hours:
        return f"{h:02d} {m:02d} {s:04.1f}"
    return f"{sign}{h:02d} {m:02d} {round(s):02d}" if round(s) < 60 else f"{sign}{h:02d} {m + 1:02d} 00"


def _spans(jd, ok):
    """[(first, last)] of the runs of True in ok."""
    out, start = [], None
    for i, v in enumerate(ok):
        if v and start is None:
            start = i
        if start is not None and (not v or i == len(ok) - 1):
            out.append((jd[start], jd[i if v else i - 1]))
            start = None
    return out


def target_rows(page, row):
    """[(name, value, unit)] of targets-table row `row`; the night's rows only when it is of the date shown."""
    cell = page._cell
    try:
        ra, dec = float(cell(row, 1)), float(cell(row, 2))
    except ValueError:
        return [(translate("PlanWindow", "Name"), cell(row, 0), "")]
    rows = [
        (translate("PlanWindow", "Name"), cell(row, 0), ""),
        (translate("PlanWindow", "RA (J2000)"), _sexagesimal(ra, True), "h m s"),
        (translate("PlanWindow", "Dec (J2000)"), _sexagesimal(dec, False), "° ′ ″"),
    ]
    t = {"t0_text": cell(row, 3), "period_text": cell(row, 4)}
    if t["t0_text"] and t["period_text"]:
        rows += [
            (translate("PlanWindow", "T0"), t["t0_text"], "BJD"),
            (translate("PlanWindow", "Period"), t["period_text"], "d"),
        ]
        t0_err, p_err, _cov, estimated = ephemeris_errors(t)
        if t0_err is not None:
            how = translate("PlanWindow", "from the digits") if estimated else ""
            rows += [(translate("PlanWindow", "σ T0, σ P"), f"{t0_err:.2g} d, {p_err:.2g} d {how}".strip(), "")]
    night = page.result
    if not night or night.get("date") != page.date.date().toString("yyyy-MM-dd"):
        return [*rows, (translate("PlanWindow", "Tonight"), translate("PlanWindow", "plan the night to see it"), "")]
    entry = next((e for e in night["targets"] if e["name"] == cell(row, 0)), None)
    if entry is None:
        return [*rows, (translate("PlanWindow", "Tonight"), translate("PlanWindow", "not in the planned night"), "")]
    jd, alt = np.asarray(night["jd"]), np.asarray(entry["alt"])
    off = page.local_offset(jd[len(jd) // 2])

    def local(v):
        return Time(v + off / 24, format="jd").iso[11:16] if v else "—"

    unit = translate("PlanWindow", "local, UTC{off}").format(off=f"{off:+g}")
    lowest = np.asarray(entry.get("limit", page.min_alt.value()))
    dark = (jd >= (night["dusk"] or jd[0])) & (jd <= (night["dawn"] or jd[-1]))
    for first, last in _spans(jd, (alt >= lowest) & dark):
        rows.append((translate("PlanWindow", "Above the limit"), f"{local(first)} – {local(last)}", unit))
    top = int(np.argmax(np.where(dark, alt, -90)))
    rows.append((translate("PlanWindow", "Highest"), f"{local(jd[top])}, {alt[top]:.0f}°", unit))
    rows.append((translate("PlanWindow", "Moon distance at the highest"), f"{entry['moon_sep'][top]:.0f}", "°"))
    kinds = {
        "primary": translate("PlanWindow", "Minimum I / transit"),
        "secondary": translate("PlanWindow", "Minimum II"),
    }
    for e in entry["events"]:
        rows.append((kinds[e["kind"]], f"{local(e['mid'])}{_uncertainty(e)}", unit))
    return rows


def plan_inspector(win, page):
    """The inspector beside the stages: hidden until a row is chosen; follows the row, date, site and night."""
    panel = Inspector(translate("PlanWindow", "Target"))
    dock = win.set_inspector(panel)
    dock.hide()  # a small window has no room beside the stages until a target is chosen (F10 shows it)

    def refresh(*_):
        row = page.table.currentRow()
        if 0 <= row < page.table.rowCount():
            panel.set_rows(target_rows(page, row))
            dock.show()
        else:
            panel.set_rows([("", translate("PlanWindow", "Select a target to see its details"), "")])

    page.table.currentCellChanged.connect(refresh)
    page.table.itemChanged.connect(refresh)
    for box in (page.date, page.lat, page.lon, page.min_alt, page.utc_offset):
        (box.dateChanged if box is page.date else box.valueChanged).connect(refresh)
    show_night = page.show_night
    page.show_night = lambda n: (show_night(n), refresh())  # the night arrives from the engine after the date
    win.target_inspector = panel
    refresh()
