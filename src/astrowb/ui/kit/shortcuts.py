"""The keyboard shortcuts of a window, read from its actions (plans/interface.md UI-12): Help → Keyboard shortcuts
(Ctrl+/) lists them in a sheet with a search field, and a test finds a key given to two actions of one window.

    sheet = ShortcutSheet(window); sheet.show()
    duplicates(window)          # {key: [action paths]} for keys that do two things
"""

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QHeaderView, QLineEdit, QTableWidget, QTableWidgetItem, QVBoxLayout

from .dialogs import Dialog

translate = QCoreApplication.translate


def shortcuts_of(window):
    """[(where the action is, its keys)] for every action of the window's menus, toolbar and own key actions."""
    out = [(path, act) for path, act in window.commands()]
    find = getattr(window, "find_action", None)  # left out of the action search itself
    if find is not None:
        out.append((find.text().replace("&", ""), find))
    seen = {act for _, act in out}
    out += [(act.text(), act) for act in window.actions() if act not in seen and act.text()]
    rows = []
    for path, act in out:
        keys = [k.toString(QKeySequence.NativeText) for k in act.shortcuts() if not k.isEmpty()]
        if keys:
            rows.append((path, ", ".join(keys), act))
    return rows


def _active_in(act, window):
    """Whether the action's keys work in this window (a widget-scoped action of another window does not count)."""
    if act.shortcutContext() in (Qt.WindowShortcut, Qt.ApplicationShortcut):
        return True
    return window in act.associatedObjects()


def duplicates(window):
    by_key = {}
    for path, _keys, act in shortcuts_of(window):
        if not _active_in(act, window):
            continue
        for key in act.shortcuts():
            if not key.isEmpty():
                by_key.setdefault(key.toString(), set()).add((path, id(act)))
    return {key: sorted(p for p, _ in acts) for key, acts in by_key.items() if len(acts) > 1}


class ShortcutSheet(Dialog):
    def __init__(self, window):
        super().__init__(
            translate("ShortcutSheet", "Keyboard shortcuts"), window, getattr(window, "settings", None), "shortcuts"
        )
        self.search = QLineEdit(self)
        self.search.setPlaceholderText(self.tr("Find a shortcut or an action"))
        self.search.setClearButtonEnabled(True)
        self.table = QTableWidget(0, 2, self)
        self.table.setHorizontalHeaderLabels([self.tr("Action"), self.tr("Keys")])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        rows = sorted(shortcuts_of(window), key=lambda r: r[0].casefold())
        self.table.setRowCount(len(rows))
        for i, (path, keys, _act) in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(path))
            self.table.setItem(i, 1, QTableWidgetItem(keys))
        self.search.textChanged.connect(self._filter)
        lay = QVBoxLayout()
        lay.addWidget(self.search)
        lay.addWidget(self.table)
        self.body.addLayout(lay)
        if not self.size().isValid() or self.width() < 300:
            self.resize(560, 520)

    def _filter(self, text):
        words = text.casefold().split()
        for i in range(self.table.rowCount()):
            row = f"{self.table.item(i, 0).text()} {self.table.item(i, 1).text()}".casefold()
            self.table.setRowHidden(i, not all(w in row for w in words))
