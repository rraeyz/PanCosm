"""The parts of an area window's anatomy (plans/interface.md "Anatomy of an area window", UI-4), added to AreaWindow:
stages (rail + the current stage's panel) at the left, the inspector at the right, result tabs below the main view.

    win.set_stages([Stage("images", tr("Images"), images_panel, help="photometry/images"), ...])
    win.set_stage_state("images", "done"); win.show_stage("stars")
    win.set_inspector(Inspector(tr("Star")))
    win.add_result_tab("plot", tr("Plot"), plot_view)

Keys: F9 the stage panel, F10 the inspector, F11 the results, Ctrl+1 … Ctrl+9 the stages, Ctrl+Tab the next result.
"""

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QHBoxLayout, QStackedWidget, QWidget

from .rail import StagePanel, StageRail


@dataclass
class Stage:
    key: str
    title: str
    panel: object  # a StagePanel, or any widget (wrapped in one)
    help: str | None = None


class Anatomy:
    """Mixed into AreaWindow; uses its _dock (docks remembered with the layout) and its key."""

    def set_stages(self, stages):
        self.stages = {s.key: s for s in stages}
        self.rail = StageRail([(s.key, s.title) for s in stages], self)
        self.stage_stack = QStackedWidget(self)
        self.stage_panels = {}
        for s in stages:
            panel = s.panel
            if not isinstance(panel, StagePanel):
                panel = StagePanel(s.title, s.help, self)
                panel.add(s.panel)
            if s.help:
                panel.help_requested.connect(lambda _h, k=self.key: self.help_requested.emit(k))
            self.stage_panels[s.key] = panel
            self.stage_stack.addWidget(panel)
        holder = QWidget(self)
        row = QHBoxLayout(holder)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        row.addWidget(self.rail)
        row.addWidget(self.stage_stack, 1)
        self.stage_stack.setMinimumWidth(280)
        self.rail.stage_chosen.connect(self.show_stage)
        dock = self._dock("stages", self.tr("Stages"), holder, Qt.LeftDockWidgetArea)
        self._key_action(self.tr("Show or hide the stage panel"), "F9", lambda: dock.setVisible(not dock.isVisible()))
        for i, s in enumerate(stages[:9], 1):
            self._key_action(s.title, f"Ctrl+{i}", lambda _on=False, k=s.key: self.show_stage(k))
        if stages:
            self.show_stage(stages[0].key)

    def show_stage(self, key):
        self.rail.set_current(key)
        self.stage_stack.setCurrentWidget(self.stage_panels[key])
        self.docks["stages"].show()

    def current_stage(self):
        return self.rail.current

    def set_stage_state(self, key, state):
        """empty | current | done | attention, set by the area from its session state."""
        self.rail.set_state(key, state)

    def set_inspector(self, widget):
        dock = self._dock("inspector", self.tr("Inspector"), widget, Qt.RightDockWidgetArea)
        self._key_action(self.tr("Show or hide the inspector"), "F10", lambda: dock.setVisible(not dock.isVisible()))
        return dock

    def add_result_tab(self, key, title, widget):
        """A tab of the results dock below the main view (tabs share the room; any can be pulled out)."""
        first = not getattr(self, "result_keys", None)
        self.result_keys = [*getattr(self, "result_keys", []), key]
        dock = self._dock(f"result_{key}", title, widget, Qt.BottomDockWidgetArea)
        if first:
            self._key_action(self.tr("Show or hide the results"), "F11", self._toggle_results)
            self._key_action(self.tr("Next result tab"), "Ctrl+Tab", self._next_result)
        return dock

    def _results(self):
        return [self.docks[f"result_{k}"] for k in getattr(self, "result_keys", [])]

    def _toggle_results(self):
        docks = self._results()
        show = not any(d.isVisible() for d in docks)
        for d in docks:
            d.setVisible(show)

    def _next_result(self):
        docks = [d for d in self._results() if d.isVisible()]
        if not docks:
            return
        shown = [d for d in docks if not d.visibleRegion().isEmpty()]
        i = docks.index(shown[0]) if shown else -1
        docks[(i + 1) % len(docks)].raise_()

    def _key_action(self, text, keys, slot):
        act = QAction(text, self)
        act.setShortcut(QKeySequence(keys))
        act.setShortcutContext(Qt.WindowShortcut)
        act.triggered.connect(slot)
        self.addAction(act)
        return act
