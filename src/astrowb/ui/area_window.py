"""The frame every area window shares (Photometry, Spectroscopy, O-C, …): a window of its own, like a program of
its own, as MaxIm DL and AstroImageJ give each tool its menus and toolbar.

An area declares what it has — its central view, an optional steps panel, its panels, menus, toolbar actions and
undo stack — and the frame adds what every window needs: File / Edit / View / Window / Help menus, a status bar,
panels that can be pulled out, tabbed and moved to a second monitor, and a layout remembered per area with a way
back to the first layout (NINA users break their docked layouts and need "Reset layout")."""

import json
from pathlib import Path

from PySide6.QtCore import QByteArray, QEvent, Qt, Signal
from PySide6.QtGui import QAction, QGuiApplication, QKeySequence
from PySide6.QtWidgets import (
    QDialog,
    QDockWidget,
    QFileDialog,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QToolBar,
    QToolButton,
    QVBoxLayout,
)


class AreaWindow(QMainWindow):
    """key: stable id of the area (settings, object names; never translated). panels: [(id, title, widget,
    Qt.DockWidgetArea)]. menus: [(title, [QAction or None for a separator])]. toolbar: [QAction or None].
    open_files: the area's handler for files opened or dropped on the window ([paths]), with file_filter for the
    dialog. session: (get, set) — the area's state as a JSON-ready dict, and how to put it back (File → Save /
    Open session, as AstroImageJ's "Save all")."""

    SESSION_VERSION = 1
    RECENT = 10

    help_requested = Signal(str)  # the area's key: open its page of the guide
    _registry = []  # every area window made; shown() / alive() are what the Window menus and tasks use

    @classmethod
    def alive(cls):
        from shiboken6 import isValid

        cls._registry[:] = [w for w in cls._registry if isValid(w)]  # windows of closed main windows are gone
        return list(cls._registry)

    @classmethod
    def shown(cls):
        return [w for w in cls.alive() if w.isVisible()]

    def __init__(self, key, title, settings, central, steps=None, panels=(), menus=(), toolbar=(), undo_stack=None,
                 open_files=None, file_filter="", session=None, parent=None):  # fmt: skip
        super().__init__(parent)
        self.key, self.settings, self.undo_stack = key, settings, undo_stack
        self.open_files_handler, self.file_filter, self.session = open_files, file_filter, session
        self.setAcceptDrops(open_files is not None)
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
        self._icon_kinds = {}  # action -> icon kind (ui/icons.py), painted again when the theme changes
        self._build_menus(menus)
        self.statusBar().showMessage(self.tr("Ready"))
        self._build_task_bar()
        self._fit_screen()
        self._first_sizes()
        self._first_state = self.saveState()  # what Reset layout goes back to
        self._restore()
        AreaWindow._registry.append(self)

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
        if self.open_files_handler is not None:
            self._action(
                file_menu, self.tr("&Open…"), self.open_dialog, QKeySequence.Open,
                self.tr("Choose files for this window (you can also drop them on it)"),
            )  # fmt: skip
            self.recent_menu = file_menu.addMenu(self.tr("Open &recent"))
            self.recent_menu.aboutToShow.connect(self._fill_recent)
            file_menu.addSeparator()
        if self.session is not None:
            self._action(
                file_menu, self.tr("&Save session…"), self.save_session_dialog, QKeySequence.Save,
                self.tr("Keep everything chosen in this window (data, stars, settings) in one file to go on later"),
            )  # fmt: skip
            self._action(
                file_menu, self.tr("Open s&ession…"), self.open_session_dialog, None,
                self.tr("Go on with work saved earlier with Save session"),
            )  # fmt: skip
            file_menu.addSeparator()
        self._action(file_menu, self.tr("&Close window"), self.close, QKeySequence.Close)
        edit = bar.addMenu(self.tr("&Edit"))
        self.edit_menu = edit
        if self.undo_stack is not None:
            undo = self.undo_stack.createUndoAction(self, self.tr("&Undo"))
            undo.setShortcut(QKeySequence.Undo)
            redo = self.undo_stack.createRedoAction(self, self.tr("&Redo"))
            keys = [QKeySequence("Ctrl+Y"), QKeySequence("Ctrl+Shift+Z")] + QKeySequence.keyBindings(QKeySequence.Redo)
            redo.setShortcuts(list({k.toString(): k for k in keys}.values()))  # a key twice: ambiguous, does nothing
            edit.addActions([undo, redo])
            self.undo_action, self.redo_action = undo, redo
            edit.addSeparator()
        self.find_action = self._action(
            edit, self.tr("Find an action…"), self.find_command, "Ctrl+K",
            self.tr("Type a few letters of what you want to do: every menu and toolbar action of this window is found"),
        )  # fmt: skip
        view = bar.addMenu(self.tr("&View"))
        self.view_menu = view
        for dock in self.docks.values():
            act = dock.toggleViewAction()
            act.setToolTip(self.tr("Show or hide this panel"))
            view.addAction(act)
        tb = self.toolbar.toggleViewAction()
        tb.setText(self.tr("Toolbar"))
        view.addAction(tb)
        self.toolbar_text_action = self._action(
            view, self.tr("Toolbar &text"), self._toolbar_text_changed,
            tip=self.tr("The names beside the toolbar's icons (kept for next time)"),
        )  # fmt: skip
        self.toolbar_text_action.setCheckable(True)
        self.toolbar_text_action.setChecked(bool(self.settings.get("ui.toolbar_text", False)))
        self._toolbar_text_changed()
        view.addSeparator()
        # Ctrl+Shift: Ctrl++ / Ctrl+- zoom the images of the windows that show them
        sizes = (
            (self.tr("&Larger text"), 1, "Ctrl+Shift++"),
            (self.tr("&Smaller text"), -1, "Ctrl+Shift+-"),
            (self.tr("&Normal text size"), 0, "Ctrl+Shift+0"),
        )
        for text, step, key in sizes:
            self._action(view, text, lambda s=step: self.change_font(s), key,
                         self.tr("The size of the text in every window (kept for next time)"))  # fmt: skip
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
        self._action(
            help_menu, self.tr("Report a problem…"), self.report_problem, None,
            self.tr("Makes one file with the error log, the version, the system and the last steps, to send to the "
                    "developer. Your data files are not in it."),
        )  # fmt: skip

    # --- long work ------------------------------------------------------------
    def _build_task_bar(self):
        self._tasks = {}  # id -> task running for this window
        self.task_progress = QProgressBar(self)
        self.task_progress.setMaximumWidth(220)
        self.task_progress.setRange(0, 100)
        self.task_cancel = QToolButton(self)
        self.task_cancel.setText(self.tr("Cancel"))
        self.task_cancel.setToolTip(self.tr("Stop the work running for this window"))
        self.task_cancel.clicked.connect(self.cancel_tasks)
        for w in (self.task_progress, self.task_cancel):
            self.statusBar().addPermanentWidget(w)
            w.hide()

    def track(self, task):
        """Show a task started for this window (engine task: name, state, progress, message) in its status bar."""
        self._tasks[task.id] = task
        self.task_update(task)

    def task_update(self, task):
        """Called on the GUI thread on every update of a tracked task (the main window routes them)."""
        if task.id not in self._tasks:
            return
        from .messages import translate
        from .step_names import step_name

        name = step_name(task.name)
        running = [t for t in self._tasks.values() if not t.finished]
        if task.finished:
            self._tasks.pop(task.id, None)
            ends = {
                "done": self.tr("{name}: finished"),
                "failed": self.tr("{name}: failed (see the message)"),
                "cancelled": self.tr("{name}: cancelled"),
            }
            self.statusBar().showMessage(ends.get(task.state, "{name}").format(name=name))
            if not self.isActiveWindow():  # long work ended while the user was in another window
                from PySide6.QtWidgets import QApplication

                QApplication.alert(self)
            running = [t for t in self._tasks.values() if not t.finished]
        else:
            self.statusBar().showMessage(f"{name} — {translate(task.message)}".rstrip(" —"))
        shown = running[-1] if running else None
        for w in (self.task_progress, self.task_cancel):
            w.setVisible(shown is not None)
        if shown is not None:
            self.task_progress.setValue(int(shown.progress * 100))
            extra = len(running) - 1
            self.task_progress.setFormat("%p %" if not extra else self.tr("%p % (+{n} more)").format(n=extra))

    def cancel_tasks(self):
        for task in list(self._tasks.values()):
            task.cancel()
        self.statusBar().showMessage(self.tr("Stopping…"))

    # --- files ----------------------------------------------------------------
    def recent(self):
        return [p for p in self.settings.get(f"area.{self.key}.recent", []) if Path(p).exists()]

    def _remember(self, paths):
        old = self.settings.get(f"area.{self.key}.recent", [])
        new = [str(p) for p in paths] + [p for p in old if p not in map(str, paths)]
        self.settings.set(f"area.{self.key}.recent", new[: self.RECENT])

    def _fill_recent(self):
        self.recent_menu.clear()
        files = self.recent()
        for path in files:
            self._action(self.recent_menu, Path(path).name, lambda p=path: self.open_files([p]), tip=path)
        if not files:
            self.recent_menu.addAction(self.tr("(none yet)")).setEnabled(False)

    def open_dialog(self):
        paths, _ = QFileDialog.getOpenFileNames(self, self.tr("Open"), "", self.file_filter)
        if paths:
            self.open_files(paths)

    def open_files(self, paths):
        paths = [str(Path(p)) for p in paths]  # one spelling per file (a dropped file came with / on Windows)
        self._remember(paths)
        self.open_files_handler(paths)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if paths:
            event.acceptProposedAction()
            self.open_files(paths)

    def save_session(self, path):
        from .. import __version__

        doc = {
            "area": self.key,
            "version": self.SESSION_VERSION,
            "app_version": __version__,
            "state": self.session[0](),
        }
        tmp = Path(path).with_suffix(".tmp")
        tmp.write_text(json.dumps(doc, indent=1), encoding="utf-8")
        tmp.replace(path)  # a crash never leaves half a session file
        self.statusBar().showMessage(self.tr("Session saved: {path}").format(path=path))

    def open_session(self, path):
        """Returns None when opened, else the reason it could not be (also shown to the user)."""
        try:
            doc = json.loads(Path(path).read_text(encoding="utf-8"))
            if not isinstance(doc, dict) or "state" not in doc:
                raise ValueError
        except (OSError, ValueError):
            why = self.tr("{file} is not a session file, or it is damaged.").format(file=Path(path).name)
        else:
            if doc.get("area") != self.key:
                why = self.tr("{file} is a session of another window ({area}): open it there.").format(
                    file=Path(path).name, area=doc.get("area")
                )
            elif int(doc.get("version", 1)) > self.SESSION_VERSION:
                why = self.tr(
                    "{file} was saved by a newer version of the application: update it to open this session."
                ).format(file=Path(path).name)
            else:
                self.session[1](doc["state"])
                self.statusBar().showMessage(self.tr("Session opened: {path}").format(path=path))
                return None
        QMessageBox.warning(self, self.tr("Open session"), why)
        return why

    def save_session_dialog(self):
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save session"), f"{self.key}.session.json", self.tr("Session (*.session.json)")
        )
        if path:
            self.save_session(path)

    def open_session_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, self.tr("Open session"), "", self.tr("Session (*.session.json)"))
        if path:
            self.open_session(path)

    def change_font(self, step):
        from PySide6.QtWidgets import QApplication

        from . import theme

        size = theme.change_font(QApplication.instance(), self.settings, step)
        self.statusBar().showMessage(self.tr("Text size: {pt:g} pt").format(pt=size))
        return size

    def report_problem(self, path=None):
        from .report import report_dialog

        return report_dialog(self, self.settings, getattr(self.parent(), "engine", None), path)

    def commands(self):
        """[(path shown, action)] of every action of the menus and the toolbar, e.g. "View › Reset layout"."""
        self._fill_window_menu()
        out, seen = [], {self.find_action}

        def walk(menu, path):
            for act in menu.actions():
                if act.menu() is not None:
                    walk(act.menu(), path + [_plain(act.text())])
                elif act.text() and not act.isSeparator() and act not in seen:
                    seen.add(act)
                    out.append((" › ".join(path + [_plain(act.text())]), act))

        for top in self.menuBar().actions():
            if top.menu() is not None:
                walk(top.menu(), [_plain(top.text())])
        for act in self.toolbar.actions():
            if act.text() and not act.isSeparator() and act not in seen:
                seen.add(act)
                out.append((_plain(act.text()), act))
        return out

    def find_command(self):
        dialog = CommandSearch(self.commands(), self)
        dialog.move(self.mapToGlobal(self.rect().center()) - dialog.rect().center())
        dialog.show()
        dialog.search.setFocus()
        return dialog

    def _fill_window_menu(self):
        self.window_menu.clear()
        main = self.parent() if self.parent() is not None else None
        if main is not None:
            self._action(self.window_menu, self.tr("Main window"), lambda: _raise(main))
            self.window_menu.addSeparator()
        for win in AreaWindow.shown():
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

    def add_menus(self, menus, toolbar=()):
        """The area's own menus [(title, [QAction or None])], placed before Window, and toolbar actions, for windows
        whose actions are known only after the window is built."""
        for title, actions in menus:
            menu = QMenu(title, self)
            for act in actions:
                menu.addSeparator() if act is None else menu.addAction(act)
            self.menuBar().insertMenu(self.window_menu.menuAction(), menu)
        for act in toolbar:
            self.toolbar.addSeparator() if act is None else self.toolbar.addAction(act)
        if toolbar:
            self.toolbar.setVisible(True)

    def set_icons(self, kinds):
        """{action: icon kind}: the actions get the icons of ui/icons.py, the same in every window."""
        self._icon_kinds.update(kinds)
        self._paint_icons()

    def _paint_icons(self):
        from .icons import icon

        for act, kind in self._icon_kinds.items():
            act.setIcon(icon(kind, self))

    def _toolbar_text_changed(self):
        on = self.toolbar_text_action.isChecked()
        self.settings.set("ui.toolbar_text", on)
        # icons only by default (AstroImageJ); an action without an icon still shows its name
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon if on else Qt.ToolButtonIconOnly)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.PaletteChange and getattr(self, "_icon_kinds", None):
            self._paint_icons()  # the symbols take the text colour of the new theme

    def reset_layout(self):
        for dock in self.docks.values():
            dock.setFloating(False)
        self.restoreState(self._first_state)
        for dock in self.docks.values():
            dock.show()

    def showEvent(self, event):
        super().showEvent(event)
        # the window opens with the keyboard on its view, not in its first text box: a text box takes Ctrl+Z for
        # its own typing, and Undo of a star marked did nothing in the new Photometry window
        central = self.centralWidget()
        if central is not None:
            central.setFocusPolicy(Qt.StrongFocus)
            central.setFocus(Qt.OtherFocusReason)

    def closeEvent(self, event):
        self.save_layout()
        super().closeEvent(event)


def _raise(window):
    window.show()
    window.setWindowState(window.windowState() & ~Qt.WindowMinimized)
    window.raise_()
    window.activateWindow()


def _plain(text):
    return text.replace("&&", "\0").replace("&", "").replace("\0", "&")


class CommandSearch(QDialog):
    """Ctrl+K: a box that lists the window's actions matching what is typed (every word, in any order, in the
    interface language); Enter or a double click runs the one chosen. Keeps the toolbar short without hiding
    anything."""

    def __init__(self, commands, parent=None):
        super().__init__(parent, Qt.Popup)
        self.commands = commands
        lay = QVBoxLayout(self)
        self.search = QLineEdit(self)
        self.search.setPlaceholderText(self.tr("Type what you want to do…"))
        self.search.setToolTip(self.tr("Words in any order; ↑ ↓ choose, Enter runs, Esc closes"))
        self.list = QListWidget(self)
        lay.addWidget(self.search)
        lay.addWidget(self.list)
        self.resize(460, 320)
        self.search.textChanged.connect(self._filter)
        self.search.installEventFilter(self)
        self.search.returnPressed.connect(self.run)
        self.list.itemActivated.connect(lambda _item: self.run())
        self._filter("")

    def _filter(self, text):
        words = text.casefold().split()
        self.list.clear()
        for shown, act in self.commands:
            if act.isEnabled() and all(w in shown.casefold() for w in words):
                item = QListWidgetItem(shown, self.list)
                item.setData(Qt.UserRole, act)
                if act.shortcut().toString():
                    item.setToolTip(act.shortcut().toString(QKeySequence.NativeText))
        self.list.setCurrentRow(0)

    def eventFilter(self, obj, event):
        if obj is self.search and event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Up, Qt.Key_Down):
            step = -1 if event.key() == Qt.Key_Up else 1
            self.list.setCurrentRow(max(0, min(self.list.count() - 1, self.list.currentRow() + step)))
            return True
        return super().eventFilter(obj, event)

    def run(self):
        item = self.list.currentItem()
        self.close()
        if item is not None:
            item.data(Qt.UserRole).trigger()
