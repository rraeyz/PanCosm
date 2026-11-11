"""Keys over the spectrum plot of Spectrum tools, as IRAF's splot taught many (plans/interface.md UI-12):

w  a window edge (the first press the start, the next the end)    m  centre the window on the cursor
f  fit the line in the window (Measure)                            c  a continuum point at the cursor
d  delete the continuum point nearest the cursor                   a  the whole spectrum (every plot)
"""

from PySide6.QtCore import QT_TRANSLATE_NOOP, QCoreApplication

HINT = QT_TRANSLATE_NOOP(
    "SpectrumKeys",
    "Keys over the plot: w window edges, m centre the window here, f measure, c continuum point, d delete point",
)


def connect(tab):
    """Clicks and keys of the tab's plot (tab: SpectrumToolsTab)."""
    tab.plot.canvas.mpl_connect("button_press_event", lambda event: tab.pick.isChecked() and key(tab, event, "c"))
    tab.plot.canvas.mpl_connect("key_press_event", lambda event: key(tab, event))
    tab.plot.setToolTip(QCoreApplication.translate("SpectrumKeys", HINT))
    tab._edge = None  # the first w of a pair


def key(tab, event, pressed=None):
    """One key over the plot (pressed: instead of the event's key: a click while picking points is "c"); returns
    what it did (for tests), or None."""
    x = event.xdata if event.inaxes is not None else None
    pressed = pressed or event.key
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
