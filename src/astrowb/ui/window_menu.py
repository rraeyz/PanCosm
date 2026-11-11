"""The Window menu, the tables' context menu, keys and help of the area windows: a mixin of MainWindow moved out
of main_window.py (plans/architecture.md ARC-4.4); texts keep the main window's translation context."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QFileDialog

from .kit.window import _raise as _raise_window

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("MainWindow", "…") calls


class WindowMenu:
    """Methods of MainWindow (self is the main window)."""

    def _fill_window_menu(self):
        from .kit.window import AreaWindow, _raise
        from .start_page import areas

        self.window_menu.clear()
        self._action(self.window_menu, translate("MainWindow", "Main window"), lambda: _raise(self))
        for key in ("start", "project", "guide"):  # the main window's own pages (the sidebar is gone)
            self._action(self.window_menu, self._titles[key], lambda k=key: (_raise(self), self.show_workspace(k)))
        self.window_menu.addSeparator()
        open_now = AreaWindow.shown()
        for win in open_now:
            self._action(self.window_menu, win.windowTitle(), lambda w=win: _raise(w))
        if open_now:
            self.window_menu.addSeparator()
        sub = self.window_menu.addMenu(translate("MainWindow", "Open an area"))
        for key, _, name, _ in areas():
            self._action(sub, name, lambda k=key: self.open_area(k))

    def _table_menu(self, table, pos):
        from PySide6.QtWidgets import QApplication, QMenu

        from .plot.export import export_table, selected_text, table_rows

        menu = QMenu(table)
        selected = menu.addAction(translate("MainWindow", "Copy") + "\tCtrl+C")
        selected.setEnabled(bool(table.selectedIndexes()))
        copy = menu.addAction(translate("MainWindow", "Copy table"))
        export = menu.addAction(translate("MainWindow", "Export table (CSV or LaTeX)…"))
        chosen = menu.exec(table.viewport().mapToGlobal(pos))
        if chosen is selected:
            QApplication.clipboard().setText(selected_text(table))
        elif chosen is export:
            path, _ = QFileDialog.getSaveFileName(
                self, translate("MainWindow", "Export table"), "table.csv", "CSV (*.csv);;LaTeX (*.tex)"
            )
            if path:
                export_table(table, path)
        elif chosen is copy:
            header, rows = table_rows(table)
            QApplication.clipboard().setText("\n".join("\t".join(r) for r in [header, *rows]))

    def _show_key(self, key):
        if key in self.WINDOWED:  # opens its window; the main window keeps showing what it showed
            self.open_area(key)
        elif key:
            page = getattr(self, self.PAGES[key])
            self.pages.setCurrentWidget(self._frames.get(page, page))
            self._key = key
            self._follow_undo(page)

    def _follow_undo(self, page=None):
        """Edit -> Undo / Redo act on the page shown (on its open tab when it has tabs)."""
        if not hasattr(self, "undo_group"):  # pages shown while the window is built, before its menus
            return
        page = page or getattr(self, self.PAGES.get(self._key, ""), None)
        tabs = page if hasattr(page, "currentWidget") else getattr(page, "tabs", None)
        if tabs is not None and not getattr(tabs, "_follows_undo", False):
            tabs.currentChanged.connect(lambda _=0: self._follow_undo())
            tabs._follows_undo = True
        inner = tabs.currentWidget() if tabs is not None else None
        stack = getattr(inner, "undo_stack", None) or getattr(page, "undo_stack", None)
        if stack is not None and stack not in self.undo_group.stacks():
            self.undo_group.addStack(stack)
        self.undo_group.setActiveStack(stack)

    def _help_for(self, key):
        """F1 in an area window: the guide, filtered to that area; a guide anchor ("photometry-apertures", from a
        section's or a stage's help button) opens that topic."""
        from .start_page import areas

        self.show_workspace("guide")
        _raise_window(self)
        if "-" in key and self.guide_page.show_anchor(key):
            return
        name = next((n for k, _, n, _ in areas() if k == key), "")
        self.guide_page.search.setText(name)
