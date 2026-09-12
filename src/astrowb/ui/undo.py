"""Undo / redo of the user's edits (Edit menu, Ctrl+Z / Ctrl+Y), page by page.

A page that takes part keeps a QUndoStack and two methods: undo_state() returns what the user edits there (plain
values: lists, tuples, numbers, text) and set_undo_state(state) shows such a state again. Every edit is wrapped
in edit(text, function): the state before and after is stored, so any edit can be taken back and done again,
whatever it changed. Text fields keep their own Ctrl+Z while they have the keyboard.
"""

import numpy as np
from PySide6.QtGui import QUndoCommand, QUndoStack


def same(a, b):
    """Equality of two states that may hold numpy arrays (a spectrum's flux)."""
    if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
        if not (isinstance(a, np.ndarray) and isinstance(b, np.ndarray)) or a.shape != b.shape:
            return False
        return bool(np.array_equal(a, b, equal_nan=a.dtype.kind == "f" and b.dtype.kind == "f"))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b, strict=True))
    return a == b


def track_typing(page, table, text):
    """Values typed into a table become undoable steps named text (changes made by an edit() are part of it)."""
    page._typed_from = page.undo_state()

    def typed(_item):
        if page._restoring or page._editing:  # a change made by an edit, recorded with it
            return
        page.record(text, page._typed_from)
        page._typed_from = page.undo_state()

    def moved(_i):
        import shiboken6

        if shiboken6.isValid(table):  # a closing window deletes its panels before the page's undo stack
            page._typed_from = page.undo_state()

    table.itemChanged.connect(typed)
    page.undo_stack.indexChanged.connect(moved)


class _Snapshot(QUndoCommand):
    def __init__(self, page, before, after, text):
        super().__init__(text)
        self._page, self._before, self._after, self._done = page, before, after, True

    def redo(self):
        if self._done:  # the edit itself has just made this state: nothing to do the first time
            self._done = False
            return
        self._page._restore_undo(self._after)

    def undo(self):
        self._page._restore_undo(self._before)


class Undoable:
    """Mixin for a page widget (call init_undo() in __init__)."""

    def init_undo(self):
        self.undo_stack = QUndoStack(self)
        self._restoring = self._editing = False

    def edit(self, text, function, *args, **kwargs):
        """Run function as one undoable step named text (shown in the Edit menu)."""
        if self._restoring or self._editing:  # inside another edit: part of that step
            return function(*args, **kwargs)
        before = self.undo_state()
        self._editing = True
        try:
            out = function(*args, **kwargs)
        finally:
            self._editing = False
        after = self.undo_state()
        if not same(before, after):
            self.undo_stack.push(_Snapshot(self, before, after, text))
        return out

    def record(self, text, before):
        """An edit already made (a value typed into a table): from the state `before` to the present one."""
        if self._restoring or self._editing:
            return
        after = self.undo_state()
        if not same(before, after):
            self.undo_stack.push(_Snapshot(self, before, after, text))

    def _restore_undo(self, state):
        self._restoring = True
        try:
            self.set_undo_state(state)
        finally:
            self._restoring = False
