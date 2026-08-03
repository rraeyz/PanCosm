"""Undo / redo of the user's edits (Edit menu, Ctrl+Z / Ctrl+Y), page by page.

A page that takes part keeps a QUndoStack and two methods: undo_state() returns what the user edits there (plain
values: lists, tuples, numbers, text) and set_undo_state(state) shows such a state again. Every edit is wrapped
in edit(text, function): the state before and after is stored, so any edit can be taken back and done again,
whatever it changed. Text fields keep their own Ctrl+Z while they have the keyboard.
"""

from PySide6.QtGui import QUndoCommand, QUndoStack


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
        self._restoring = False

    def edit(self, text, function, *args, **kwargs):
        """Run function as one undoable step named text (shown in the Edit menu)."""
        if self._restoring:
            return function(*args, **kwargs)
        before = self.undo_state()
        out = function(*args, **kwargs)
        after = self.undo_state()
        if before != after:
            self.undo_stack.push(_Snapshot(self, before, after, text))
        return out

    def record(self, text, before):
        """An edit already made (a value typed into a table): from the state `before` to the present one."""
        after = self.undo_state()
        if not self._restoring and before != after:
            self.undo_stack.push(_Snapshot(self, before, after, text))

    def _restore_undo(self, state):
        self._restoring = True
        try:
            self.set_undo_state(state)
        finally:
            self._restoring = False
