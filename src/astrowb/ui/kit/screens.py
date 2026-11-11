"""Windows over several monitors (plans/interface.md UI-14): tile the open windows side by side on one screen, or
bring them all to it (a monitor that was unplugged, a projector at a talk)."""

from PySide6.QtGui import QGuiApplication


def _room(screen):
    return (screen or QGuiApplication.primaryScreen()).availableGeometry()


def tile(windows, screen=None):
    """The windows side by side in columns over the screen's free area (the task bar left out); returns the
    geometries given, in the order of windows."""
    windows = [w for w in windows if w.isVisible()]
    if not windows:
        return []
    room = _room(screen)
    width = room.width() // len(windows)
    out = []
    for i, w in enumerate(windows):
        w.showNormal()  # a maximised window ignores a new size
        w.setGeometry(room.x() + i * width, room.y(), width, room.height())
        out.append(w.geometry())
    return out


def gather(windows, screen=None):
    """Every window onto the screen, each keeping its size where it fits, cascaded from the top left."""
    room = _room(screen)
    step = 32
    for i, w in enumerate(x for x in windows if x.isVisible()):
        w.showNormal()
        w.resize(min(w.width(), room.width()), min(w.height(), room.height()))
        w.move(room.x() + (i * step) % max(room.width() - w.width(), 1),
               room.y() + (i * step) % max(room.height() - w.height(), 1))  # fmt: skip
