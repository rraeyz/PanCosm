"""Two-way links between kit controls and paths of a session store (core/state.py, ARC-5), and autosave.

    bind(radius_spin, store, "apertures.r_ap", self.tr("aperture radius"))
    Autosave(store, project)        # store JSON into the project 2 s after the last change, and on flush()

A bound control writes every user change into the store (one undo step, typing merged) and follows every change of
the store (undo, redo, an opened session), so a panel never writes undo code of its own.
"""

from PySide6.QtCore import QSignalBlocker, QTimer
from PySide6.QtWidgets import QAbstractButton, QAbstractSpinBox, QComboBox, QLineEdit, QPlainTextEdit

AUTOSAVE_MS = 2000


def _parts(widget):
    """(signal the user changes it with, read(), write(value)) for a kit control."""
    if hasattr(widget, "kit_binding"):  # kit controls that are not a Qt control of one of the kinds below
        return widget.kit_binding()
    if isinstance(widget, QAbstractSpinBox):
        return widget.valueChanged, widget.value, widget.setValue
    if isinstance(widget, QAbstractButton):
        return widget.toggled, widget.isChecked, lambda v: widget.setChecked(bool(v))
    if isinstance(widget, QComboBox):  # the item's data when it has one, else its text

        def read():
            data = widget.currentData()
            return widget.currentText() if data is None else data

        def write(v):
            i = widget.findData(v)
            widget.setCurrentIndex(i if i >= 0 else widget.findText(str(v)))

        return widget.currentIndexChanged, read, write
    if isinstance(widget, QLineEdit):
        return widget.textEdited, widget.text, lambda v: widget.setText("" if v is None else str(v))
    if isinstance(widget, QPlainTextEdit):
        return widget.textChanged, widget.toPlainText, lambda v: widget.setPlainText("" if v is None else str(v))
    raise TypeError(f"no binding for {type(widget).__name__}")


def bind(widget, store, path, text=None):
    """Keep widget and store[path] equal both ways. The store's value wins at the start when it has one."""
    signal, read, write = _parts(widget)

    def show(paths=None):
        if paths is not None and not any(path == p or path.startswith(p + ".") for p in paths):
            return
        value = store.get(path)
        if value is not None and value != read():
            with QSignalBlocker(widget):
                write(value)

    if store.get(path) is None:
        store.default(path, read())
    show()
    signal.connect(lambda *_: store.set(path, read(), text=text))
    unsubscribe = store.subscribe(show)
    widget.destroyed.connect(lambda *_: unsubscribe())
    return widget


class Autosave:
    """Writes the store's JSON into the project (sessions table, name "last") AUTOSAVE_MS after the last change.
    Call flush() when the window closes."""

    def __init__(self, store, project, name="last"):
        self.store, self.project, self.name = store, project, name
        self.timer = QTimer(singleShot=True, interval=AUTOSAVE_MS, timeout=self.flush)
        store.subscribe(lambda _paths: self.timer.start())

    def flush(self):
        self.timer.stop()
        # shortcut: without a project nothing is autosaved; the user data folder comes with the first area moved
        if self.project is not None and self.store.modified():
            self.project.save_session(self.store.area, self.store.to_json(), self.name)
