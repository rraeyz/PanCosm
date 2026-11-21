"""The "Measurements" result tab of the Images window (plans/interface.md UI-16.10): every Star / Area / Line
measurement is also a row (the tool, the file, then the values that measurement returned; blank where a value does
not apply), with the table's own Export and Delete."""

import numpy as np
from astropy.table import Table
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from .kit.table import TableView

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("Ctx", "…") calls


class MeasurementTable(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows = []  # dicts: tool, file, then the values
        self.table = TableView(self)
        self.table.set_row_actions([(self.tr("Delete"), self.delete)])
        delete = QPushButton(self.tr("Delete"), self)
        delete.clicked.connect(lambda: self.delete(self.table.selected_rows()))
        export = QPushButton(self.tr("Export…"), self)
        export.clicked.connect(self.table._export_dialog)
        row = QHBoxLayout()
        row.addWidget(delete)
        row.addWidget(export)
        row.addStretch(1)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addLayout(row)
        lay.addWidget(self.table)

    def add(self, tool, file, values):
        self.rows.append({"tool": tool, "file": file, **values})
        self._show()

    def delete(self, rows):
        self.rows = [r for i, r in enumerate(self.rows) if i not in set(rows)]
        self._show()

    def _show(self):
        t = Table()
        t["tool"] = [r["tool"] for r in self.rows]
        t["file"] = [r["file"] for r in self.rows]
        for name in dict.fromkeys(k for r in self.rows for k in r if k not in ("tool", "file")):
            t[name] = np.array([r.get(name, np.nan) for r in self.rows], dtype=float)
        self.table.set_table(t)


def record(page, tool, values):
    """Append one measurement of the page to its window's Measurements tab (made at the first one)."""
    win = page.window()
    if page.isHidden() or not hasattr(win, "add_result_tab"):  # Photometry's unseen image tools: its own docks
        return None
    table = getattr(page, "measurement_table", None)
    if table is None:
        table = page.measurement_table = MeasurementTable(win)
        win.add_result_tab("measurements", translate("ImageWindow", "Measurements"), table)
    path = getattr(page._files_window(), "current_path", None)
    table.add(tool, str(path.name if hasattr(path, "name") else path or ""), values)
    return table


def star_values(s, wcs):
    """The numbers star_info returned (FITS pixels are 1-based), plus the sky position when there is a WCS."""
    v = {"x": s["x"] + 1, "y": s["y"] + 1}
    if wcs is not None:
        v["ra"], v["dec"] = (float(c) for c in wcs.celestial.pixel_to_world_values(s["x"], s["y"]))
    keys = ("peak", "background", "net_counts", "net_counts_err", "snr", "instrumental_mag", "instrumental_mag_err",
            "fwhm", "hfd", "ellipticity", "position_angle", "r_ap", "r_in", "r_out", "pixels")  # fmt: skip
    return v | {k: float(s[k]) for k in keys if k in s}


def area_values(a):
    keys = ("width", "height", "pixels", "sum", "mean", "median", "std", "mad_std", "min", "max")
    return {k: float(a[k]) for k in keys} | {"x0": a["x0"] + 1, "y0": a["y0"] + 1, "x1": a["x1"] + 1, "y1": a["y1"] + 1}


def line_values(p, x0, y0, x1, y1):
    vals = np.asarray(p["values"])
    return {
        "x0": x0 + 1, "y0": y0 + 1, "x1": x1 + 1, "y1": y1 + 1, "length": float(p["length"]),
        "angle": float(p["angle"]), "min": float(vals.min()), "max": float(vals.max()), "mean": float(vals.mean()),
    }  # fmt: skip
