"""Keys over the spectrum plot of Spectrum tools, as IRAF's splot taught many (plans/interface.md UI-12):

w  a window edge (the first press the start, the next the end)    m  centre the window on the cursor
f  fit the line in the window (Measure)                            c  a continuum point at the cursor
d  delete the continuum point nearest the cursor                   a  the whole spectrum (every plot)
"""

from PySide6.QtCore import QT_TRANSLATE_NOOP, QCoreApplication

from .plot.toolbar import PlotToolbar

HINT = QT_TRANSLATE_NOOP(
    "SpectrumKeys",
    "Keys over the plot: w window edges, m centre the window here, f measure, c continuum point, d delete point",
)


def connect(tab):
    """Clicks, keys and the dragged span of the tab's plot (tab: SpectrumToolsTab)."""
    tab.plot.parent().findChild(PlotToolbar).set_mode("range")  # a drag selects the measuring window
    tab.plot.range_selected.connect(tab._selected)
    tab.plot.plot_clicked.connect(lambda _panel, x, _y: tab.pick.isChecked() and key(tab, "c", x))
    tab.plot.key_pressed.connect(lambda letter, x: key(tab, letter, x))
    tab.plot.setToolTip(QCoreApplication.translate("SpectrumKeys", HINT))
    tab._edge = None  # the first w of a pair


def key(tab, pressed, x):
    """One key over the plot at wavelength x (None: the cursor is outside the plot; a click while picking points is
    "c"); returns what it did (for tests), or None."""
    if pressed == "f":
        tab._measure()
        return "measure"
    if x is None or tab.wave is None:
        return None
    if pressed == "w":
        if tab._edge is None:
            tab._edge = x
            return "edge"
        lo, hi = sorted((tab._edge, x))
        tab._edge = None
        tab.lo.setValue(lo)
        tab.hi.setValue(hi)
        return "window"
    if pressed == "m":
        half = abs(tab.hi.value() - tab.lo.value()) / 2
        tab.lo.setValue(x - half)
        tab.hi.setValue(x + half)
        return "centre"
    if pressed == "c":
        tab.edit(QCoreApplication.translate("SpectrumKeys", "pick a continuum point"), tab._add_point, float(x))
        return "point"
    if pressed == "d" and tab.points:
        nearest = min(tab.points, key=lambda p: abs(p - x))
        tab.edit(QCoreApplication.translate("SpectrumKeys", "delete a continuum point"), _drop, tab, nearest)
        return "delete"
    return None


def _drop(tab, x):
    tab.points.remove(x)
    tab._plot()
