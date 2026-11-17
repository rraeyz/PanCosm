"""Hand a background thread's result to a widget's slot in the window's thread.

A thread that emits a signal of the widget itself races with the window closing: the widget can be freed by the
window's thread in the middle of the emit, which corrupts memory and crashes at a random later point. Here the
thread emits on one hub that lives as long as the program, and the slot runs only if its widget still exists.
"""

from PySide6.QtCore import QObject, Signal


class _Hub(QObject):
    arrived = Signal(object, object, object)  # owner, slot, args


def _call(owner, slot, args):
    from shiboken6 import isValid

    if isValid(owner):
        slot(*args)


_hub = None


def to_main(owner, slot):
    """Call in the window's thread; returns a function any thread may call with the slot's arguments."""
    global _hub
    if _hub is None:
        _hub = _Hub()  # parentless and never freed: emitting on it can never meet a deleted object
        _hub.arrived.connect(_call)
    hub = _hub
    return lambda *args: hub.arrived.emit(owner, slot, args)
