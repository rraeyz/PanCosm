"""The parts of an area window's anatomy (plans/interface.md "Anatomy of an area window", UI-4), added to AreaWindow:
stages (rail + the current stage's panel) at the left, the inspector at the right, result tabs below the main view.

    win.set_stages([Stage("images", tr("Images"), images_panel, help="photometry/images"), ...])
    win.set_stage_state("images", "done"); win.show_stage("stars")
    win.set_inspector(Inspector(tr("Star")))
    win.add_result_tab("plot", tr("Plot"), plot_view)

Keys: F9 the stage panel, F10 the inspector, F11 the results, Ctrl+1 … Ctrl+9 the stages, Ctrl+Tab the next result.
"""

from dataclasses import dataclass

from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QHBoxLayout, QScrollArea, QStackedWidget, QWidget

from . import layout_memory
from .fit import fit_width
from .rail import StagePanel, StageRail


@dataclass
class Stage:
    key: str
    title: str
    panel: object  # a StagePanel, or any widget (wrapped in one)
    help: str | None = None
    hint: str | None = None  # a coach mark the first time the stage is opened (kit/help.coach_mark)


class _WidthWatch(QObject):
    """Calls the window's _fit_to_width on each resize (the window class keeps its own eventFilter); not again from
    inside it: the re-layout resizes the window, which on Windows flipped the layout back within the same call (CI
    hung in setStyleSheet, 2026-11-28)."""

    def eventFilter(self, obj, event):  # noqa: N802 (Qt's name)
        if event.type() == QEvent.Resize and not getattr(obj, "_fitting", False):
            obj._fitting = True
            try:
                obj._fit_to_width()
            finally:
                obj._fitting = False
        return False


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
                # the stage's guide topic in the Help panel, as Sections do; the full guide when it names none
                panel.help_requested.connect(lambda a: self.show_help(a) or self.help_requested.emit(a))
            fit_width(panel, 360)  # a stage never pushes past its dock (user-feedback UF-9, UF-10)
            panel.width_changed.connect(lambda: self._fit_stage_dock())
            self.stage_panels[s.key] = panel
            self.stage_stack.addWidget(panel)
        holder = QWidget(self)
        row = QHBoxLayout(holder)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        row.addWidget(self.rail)
        row.addWidget(self.stage_stack, 1)
        self.rail.stage_chosen.connect(self.show_stage)
        frame = QScrollArea(self)  # the stage panels scroll themselves; a frame as the pages have (a viewport)
        frame.setWidget(holder)
        frame.setWidgetResizable(True)
        frame.setFrameShape(QScrollArea.NoFrame)
        frame.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        frame.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        def fit_frame(_pinned=None):  # the dock keeps the rail and the current stage's rows (not the widest stage's)
            panel = self.stage_stack.currentWidget()
            need = panel.minimumSizeHint().width() if panel is not None else 0
            # a wide window: 440, the rows fit in it (fit_width) and the view keeps its share however long the texts;
            # a small screen: the current stage's own width, the rest to the view
            self.stage_stack.setMinimumWidth(440 if self.width() >= 1000 else need)
            frame.setMinimumWidth(self.rail.width() + self.stage_stack.minimumWidth() + 4)

        self._fit_stage_dock = fit_frame
        self.installEventFilter(_WidthWatch(self))
        self.rail.pinned_changed.connect(fit_frame)
        dock = self._dock("stages", self.tr("Stages"), frame, Qt.LeftDockWidgetArea)
        self._key_action(self.tr("Show or hide the stage panel"), "F9", lambda: dock.setVisible(not dock.isVisible()))
        from .rail import NARROW, WIDE

        self.rail.pinned_changed.connect(  # the names take their own room, not the stage's controls'
            lambda on: self.resizeDocks([dock], [dock.width() + (WIDE - NARROW) * (1 if on else -1)], Qt.Horizontal)
        )
        self._key_action(self.tr("Run the stage's main action"), "F5", self.run_stage)
        for i, s in enumerate(stages[:9], 1):
            self._key_action(s.title, f"Ctrl+{i}", lambda _on=False, k=s.key: self.show_stage(k))
        if stages:
            self.show_stage(stages[0].key)
        self._docks_added()

    def show_stage(self, key):
        self.rail.set_current(key)
        self.stage_stack.setCurrentWidget(self.stage_panels[key])
        self._fit_stage_dock()
        self.docks["stages"].show()
        from .help import coach_mark

        coach_mark(self, self.stages[key])

    def run_stage(self):
        """F5 (UI-12): the stage's main button (the kit's "primary" one) is pressed, if it can be now."""
        from PySide6.QtWidgets import QPushButton

        panel = self.stage_panels.get(self.current_stage())
        main = [b for b in (panel.findChildren(QPushButton) if panel else []) if b.property("primary")]
        ready = [b for b in main if b.isVisible() and b.isEnabled()]
        if ready:
            ready[0].click()
        else:
            self.statusBar().showMessage(self.tr("This stage has no main action to run now"))
        return bool(ready)

    def current_stage(self):
        return self.rail.current

    def set_stage_state(self, key, state):
        """empty | current | done | attention, set by the area from its session state."""
        self.rail.set_state(key, state)

    def set_inspector(self, widget):
        dock = self._dock("inspector", self.tr("Inspector"), widget, Qt.RightDockWidgetArea)
        self._key_action(self.tr("Show or hide the inspector"), "F10", lambda: dock.setVisible(not dock.isVisible()))
        self._docks_added()
        return dock

    def add_result_tab(self, key, title, widget):
        """A tab of the results dock below the main view (tabs share the room; any can be pulled out)."""
        first = not getattr(self, "result_keys", None)
        self.result_keys = [*getattr(self, "result_keys", []), key]
        dock = self._dock(f"result_{key}", title, widget, Qt.BottomDockWidgetArea)
        if first:
            self._key_action(self.tr("Show or hide the results"), "F11", self._toggle_results)
            self._key_action(self.tr("Next result tab"), "Ctrl+Tab", self._next_result)
        self._docks_added()
        return dock

    def set_result_stale(self, key, stale=True):
        """Results of an older run stay visible, marked "out of date" in the tab's title, while their inputs have
        changed (shortcut: a title suffix, not a Badge: a dock title takes no widget beside its text)."""
        dock = self.docks[f"result_{key}"]
        base = dock.property("base_title") or dock.windowTitle()
        dock.setProperty("base_title", base)
        dock.setWindowTitle(self.tr("{title} (out of date)").format(title=base) if stale else base)

    def _docks_added(self):
        """The docks made after the window was built are part of "Reset layout" and get the saved layout, once
        the area has made them all (the first layout is what Reset goes back to, so it is taken before)."""
        self._narrow = False  # docks made just now: a small window places them too
        self._fit_to_width()
        self._first_state = self.saveState()
        if not getattr(self, "_restore_due", False):
            self._restore_due = True
            QTimer.singleShot(0, self, self._restore_docks)  # tied to the window: none after it is deleted

    def _fit_to_width(self):
        """A window under 1000 px wide (a small screen) keeps the view at half of it or more: the rail shows its
        marks, the inspector goes under the stage panel, the stage dock takes its rows' width (beside both, the view
        was squeezed to a sliver); widened again, the window goes back. Followed on every resize: a window is built
        and first shown at a default size."""
        stages, inspector = self.docks.get("stages"), self.docks.get("inspector")
        was = getattr(self, "_narrow", False)
        narrow = self.width() < (1040 if was else 1000)  # a margin: a width near 1000 does not flip back and forth
        if stages is None or narrow == was:
            return
        self._narrow = narrow
        self.rail.pin.setChecked(not narrow)
        if inspector is not None and narrow and self.dockWidgetArea(inspector) == Qt.RightDockWidgetArea:
            self.splitDockWidget(stages, inspector, Qt.Vertical)
        elif inspector is not None and not narrow and self.dockWidgetArea(inspector) == Qt.LeftDockWidgetArea:
            self.addDockWidget(Qt.RightDockWidgetArea, inspector)
        self._fit_stage_dock()
        if narrow:
            self.resizeDocks([stages], [stages.widget().minimumWidth()], Qt.Horizontal)

    def _restore_docks(self):
        self._restore_due = False
        layout_memory.restore(self)

    def set_main(self, widget):
        """The main view (an image, a spectrum, a plot); replaces the one before it."""
        self._main_stack().setCurrentWidget(self._put(widget, "main"))

    def set_empty_state(self, widget=None):
        """A view for no data (EmptyState) in place of the main view; None brings the main view back."""
        stack = self._main_stack()
        if widget is None:
            stack.setCurrentWidget(self._main) if getattr(self, "_main", None) else None
        else:
            stack.setCurrentWidget(self._put(widget, "empty"))

    def _main_stack(self):
        if not hasattr(self, "_stack"):
            self._stack = QStackedWidget(self)
            first = self.takeCentralWidget()
            self.setCentralWidget(self._stack)
            self._stack.show()
            if first is not None:
                self._stack.addWidget(first)
                self._main = first
        return self._stack

    def _put(self, widget, role):
        old = getattr(self, "_" + role, None)
        if old is not None and old is not widget:
            self._stack.removeWidget(old)
            old.deleteLater()
        setattr(self, "_" + role, widget)
        self._stack.addWidget(widget)
        return widget

    def show_help(self, anchor):
        """The Help panel at the right (UI-7) with the guide's topic; False when the anchor names none."""
        if "help" not in self.docks:
            from .help import HelpPanel

            self.help_panel = HelpPanel(self.settings.get("ui.language", "en"), self)
            self.help_panel.full_guide.connect(lambda a: self.help_requested.emit(a or self.key))
            self._dock("help", self.tr("Help"), self.help_panel, Qt.RightDockWidgetArea)
        shown = self.help_panel.show_anchor(anchor)
        self.docks["help"].setVisible(shown)
        if shown:
            self.docks["help"].raise_()
        return shown

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
