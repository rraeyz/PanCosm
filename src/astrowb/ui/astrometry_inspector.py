"""Astrometry (UI-16.11): the inspector with the selected measurement row's details, hidden until a row is chosen.
Everything shown comes from the positions the page already holds."""

from pathlib import Path

from PySide6.QtCore import QCoreApplication

from .kit.inspector import Inspector

translate = QCoreApplication.translate


def position_rows(rows, i):
    p = rows[i]
    out = [
        (translate("AstrometryWindow", "Frame"), Path(p["file"]).name, ""),
        (translate("AstrometryWindow", "Time"), p["time"], "UTC"),
        ("RA", p["ra"], "°"),
        ("Dec", p["dec"], "°"),
        ("x", p["x"], "px"),
        ("y", p["y"], "px"),
    ]
    if p["resid"] is not None:
        out.append((translate("AstrometryWindow", "Residual"), p["resid"], "″"))
        rms = (sum((r["resid"] or 0) ** 2 for r in rows) / len(rows)) ** 0.5
        out.append((translate("AstrometryWindow", "rms"), rms, "″"))
    if p.get("ast_cat"):
        out.append((translate("AstrometryWindow", "Catalogue"), p["ast_cat"], ""))
    return out


def position_inspector(win, page):
    panel = Inspector(translate("AstrometryWindow", "Measurement"))
    dock = win.set_inspector(panel)
    dock.hide()

    def show(row):
        if 0 <= row < len(page.positions):
            panel.set_rows(position_rows(page.positions, row))
            dock.show()

    page.table.currentCellChanged.connect(lambda row, *_: show(row))
    win.position_inspector = panel
