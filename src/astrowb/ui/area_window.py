"""The frame every area window shares (Photometry, Spectroscopy, O-C, …): a window of its own, like a program of
its own, as MaxIm DL and AstroImageJ give each tool its menus and toolbar.

An area declares what it has — its central view, an optional steps panel, its panels, menus, toolbar actions and
undo stack — and the frame adds what every window needs: File / Edit / View / Window / Help menus, a status bar,
panels that can be pulled out, tabbed and moved to a second monitor, and a layout remembered per area with a way
back to the first layout (NINA users break their docked layouts and need "Reset layout")."""

from PySide6.QtCore import QByteArray, Qt, Signal
from PySide6.QtGui import QAction, QGuiApplication, QKeySequence
from PySide6.QtWidgets import QDockWidget, QMainWindow, QToolBar


class AreaWindow(QMainWindow):
    """key: stable id of the area (settings, object names; never translated). panels: [(id, title, widget,
    Qt.DockWidgetArea)]. menus: [(title, [QAction or None for a separator])]. toolbar: [QAction or None]."""

    help_requested = Signal(str)  # the area's key: open its page of the guide
    open_windows = []  # every area window open, for the Window menus (main window first: see main_window)

    def __init__(self, key, title, settings, central, steps=None, panels=(), menus=(), toolbar=(), undo_stack=None,
                 parent=None):  # fmt: skip
        super().__init__(parent)
        self.key, self.settings, self.undo_stack = key, settings, undo_stack
        self.setObjectName(f"area_{key}")
        self.setWindowTitle(title)
        self.setCentralWidget(central)
        self.setDockNestingEnabled(True)
        self.docks = {}
        if steps is not None:
            self._dock("steps", self.tr("Steps"), steps, Qt.LeftDockWidgetArea)
        for pid, ptitle, widget, area in panels:
            self._dock(pid, ptitle, widget, area)
        self.toolbar = QToolBar(self.tr("Toolbar"), self)
        self.toolbar.setObjectName("toolbar")  # saveState needs it
        self.toolbar.setToolTip(self.tr("The frequent actions of this window"))
        for act in toolbar:
            self.toolbar.addSeparator() if act is None else self.toolbar.addAction(act)
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        self.toolbar.setVisible(bool(toolbar))
        self._build_menus(menus)
        self.statusBar().showMessage(self.tr("Ready"))
        self._fit_screen()
        self._first_sizes()
        self._first_state = self.saveState()  # what Reset layout goes back to
        self._restore()
        AreaWindow.open_windows.append(self)

    # --- construction -------------------------------------------------------
    def _dock(self, pid, title, widget, area):
        dock = QDockWidget(title, self)
        dock.setObjectName(f"panel_{pid}")  # stable: the saved layout finds the panel by it
        dock.setWidget(widget)
        dock.setFeatures(
            QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetClosable
        )
        self.addDockWidget(area, dock)
        others = [d for d in self.docks.values() if self.dockWidgetArea(d) == area]
        if others and area == Qt.BottomDockWidgetArea:  # panels below the view share the room as tabs
            self.tabifyDockWidget(others[0], dock)
        self.docks[pid] = dock
        return dock

    def _action(self, menu, text, slot, shortcut=None, tip=None):
        act = QAction(text, self)
        act.triggered.connect(lambda _=False: slot())
        if shortcut is not None:
            act.setShortcut(QKeySequence(shortcut))
        if tip:
            act.setToolTip(tip)
            act.setStatusTip(tip)
        menu.addAction(act)
        return act

    def _build_menus(self, menus):
        bar = self.menuBar()
        file_menu = bar.addMenu(self.tr("&File"))
        self.file_menu = file_menu
        self._action(file_menu, self.tr("&Close window"), self.close, QKeySequence.Close)
        edit = bar.addMenu(self.tr("&Edit"))
        self.edit_menu = edit
        if self.undo_stack is not None:
            undo = self.undo_stack.createUndoAction(self, self.tr("&Undo"))
            undo.setShortcut(QKeySequence.Undo)
            redo = self.undo_stack.createRedoAction(self, self.tr("&Redo"))
            redo.setShortcuts([QKeySequence.Redo, QKeySequence("Ctrl+Y")])
            edit.addActions([undo, redo])
            self.undo_action, self.redo_action = undo, redo
        view = bar.addMenu(self.tr("&View"))
        self.view_menu = view
        for dock in self.docks.values():
            act = dock.toggleViewAction()
            act.setToolTip(self.tr("Show or hide this panel"))
            view.addAction(act)
        tb = self.toolbar.toggleViewAction()
        tb.setText(self.tr("Toolbar"))
        view.addAction(tb)
        view.addSeparator()
        self._action(
            view, self.tr("&Reset layout"), self.reset_layout,
            tip=self.tr("Put every panel back where it was when the window first opened"),
        )  # fmt: skip
        for title, actions in menus:
            menu = bar.addMenu(title)
            for act in actions:
                menu.addSeparator() if act is None else menu.addAction(act)
        self.window_menu = bar.addMenu(self.tr("&Window"))
        self.window_menu.aboutToShow.connect(self._fill_window_menu)
        help_menu = bar.addMenu(self.tr("&Help"))
        self.help_menu = help_menu
        self._action(
            help_menu, self.tr("Guide for this window"), lambda: self.help_requested.emit(self.key),
            QKeySequence.HelpContents, self.tr("Opens the page of the guide that explains this window"),
        )  # fmt: skip

    def _fill_window_menu(self):
        self.window_menu.clear()
        main = self.parent() if self.parent() is not None else None
        if main is not None:
            self._action(self.window_menu, self.tr("Main window"), lambda: _raise(main))
            self.window_menu.addSeparator()
        for win in AreaWindow.open_windows:
            act = self._action(self.window_menu, win.windowTitle(), lambda w=win: _raise(w))
            act.setCheckable(True)
            act.setChecked(win is self)

    def _first_sizes(self):
        """Side panels wide enough to read (Qt starts them at their smallest: titles were cut off), the view keeps
        the most room."""
        sides = {Qt.LeftDockWidgetArea: 280, Qt.RightDockWidgetArea: 340, Qt.BottomDockWidgetArea: 220}
        for area, size in sides.items():
            docks = [d for d in self.docks.values() if self.dockWidgetArea(d) == area]
            if docks:
                along = Qt.Vertical if area == Qt.BottomDockWidgetArea else Qt.Horizontal
                self.resizeDocks(docks, [size] * len(docks), along)

    def _fit_screen(self):
        screen = self.screen() or QGuiApplication.primaryScreen()
        room = screen.availableGeometry() if screen else None
        w, h = 1366, 768
        if room is not None:
            w, h = min(w, room.width()), min(h, room.height())
        self.resize(w, h)

    # --- layout -------------------------------------------------------------
    def _restore(self):
        geometry = self.settings.get(f"area.{self.key}.geometry")
        state = self.settings.get(f"area.{self.key}.state")
        if geometry:
            self.restoreGeometry(QByteArray.fromBase64(geometry.encode()))
        if state:
            self.restoreState(QByteArray.fromBase64(state.encode()))

    def save_layout(self):
        self.settings.set(f"area.{self.key}.geometry", bytes(self.saveGeometry().toBase64()).decode())
        self.settings.set(f"area.{self.key}.state", bytes(self.saveState().toBase64()).decode())

    def reset_layout(self):
        for dock in self.docks.values():
            dock.setFloating(False)
        self.restoreState(self._first_state)
        for dock in self.docks.values():
            dock.show()

    def closeEvent(self, event):
        self.save_layout()
        if self in AreaWindow.open_windows:
            AreaWindow.open_windows.remove(self)
        super().closeEvent(event)


def _raise(window):
    window.show()
    window.setWindowState(window.windowState() & ~Qt.WindowMinimized)
    window.raise_()
    window.activateWindow()
