"""Draggable radius lines of the Apertures stage's profile plot; the three radius fields stay the source of truth."""

from functools import partial

from PySide6.QtCore import QTimer

from . import photometry_figures

GAP = 0.1  # px kept between neighbouring radii; also the snapping step


class ApertureLines:
    def __init__(self, plot, spins):
        self.plot, self.spins, self.profile, self.lines = plot, spins, None, []
        self._later = QTimer(plot)  # redraws after the event that asked: never inside a line's or a spin's own signal
        self._later.setSingleShot(True)
        self._later.timeout.connect(self._redraw)
        for s in spins:
            s.valueChanged.connect(self.refresh)

    def show(self, a):
        """The profile `a` was just drawn: remember it and make its radius lines movable."""
        self.profile = a
        self._grab()

    def _grab(self):
        self.lines = []
        for e in self.plot.items:
            if e["spec"].name == "radii":
                self.lines = e["lines"]
        for i, line in enumerate(self.lines):
            line.setMovable(True)
            line.sigPositionChangeFinished.connect(partial(self.dropped, i))

    def clamp(self, i, x):
        """Snap to 0.1 px and keep aperture < inner < outer."""
        lo = self.spins[i - 1].value() + GAP if i else self.spins[0].minimum()
        hi = self.spins[i + 1].value() - GAP if i < 2 else self.spins[2].maximum()
        return round(min(max(x, lo, self.spins[i].minimum()), hi, self.spins[i].maximum()), 1)

    def dropped(self, i, *_):
        self.spins[i].setValue(self.clamp(i, self.lines[i].value()))
        self.refresh()  # the value may be unchanged (clamped back): put the line there anyway

    def refresh(self, *_):
        """Redraw the plot with the fields' radii, once the current event is over (redrawing deletes the line that may
        be emitting the signal, which crashes pyqtgraph)."""
        self._later.start(0)

    def _redraw(self):
        """Does nothing when the plot shows something else."""
        try:
            shown = bool(self.lines) and self.lines[0].scene() is not None
        except RuntimeError:  # the line's C++ object is gone with an older figure
            shown = False
        if self.profile is None or not shown:
            return
        a = dict(zip(("r_ap", "r_in", "r_out"), (s.value() for s in self.spins), strict=True))
        self.plot.set_figure(photometry_figures.aperture_figure({**self.profile, **a}), keep=True)
        self._grab()
