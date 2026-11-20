"""Axis limits… of a plot's right-click menu (UI-10): type the range of x and y by hand."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QInputDialog, QMessageBox

translate = QCoreApplication.translate


def parse_limits(text):
    """(low, high) from "0.2, 0.8" (a comma or a space between; a decimal comma is not read); ValueError otherwise."""
    parts = text.replace(",", " ").split()
    if len(parts) != 2:
        raise ValueError(text)
    low, high = float(parts[0]), float(parts[1])
    if not low < high:
        raise ValueError(text)
    return low, high


def ask_limits(parent, ax):
    """Ask for x then y limits of the axes (an empty answer leaves that axis alone); returns whether any changed."""
    changed = False
    for name, get, put in (
        (translate("PlotLimits", "x"), ax.get_xlim, ax.set_xlim),
        (translate("PlotLimits", "y"), ax.get_ylim, ax.set_ylim),
    ):
        low, high = sorted(get())
        text, ok = QInputDialog.getText(
            parent,
            translate("PlotLimits", "Axis limits"),
            translate("PlotLimits", "Range of {axis}: lowest, highest").format(axis=name),
            text=f"{low:.6g}, {high:.6g}",
        )
        if not ok or not text.strip():
            continue
        try:
            new = parse_limits(text)
        except ValueError:
            QMessageBox.warning(
                parent, translate("PlotLimits", "Axis limits"), translate("PlotLimits", "Two numbers, the lower first")
            )
            continue
        # an inverted axis (magnitudes) stays inverted
        put(*(new[::-1] if get()[0] > get()[1] else new))
        changed = True
    return changed
