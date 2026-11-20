"""An area window's layout kept per arrangement of the screens (plans/interface.md UI-4 item 2, UI-14): geometry,
the docks (floating result tabs with the screen they were on) and whether the rail's names are pinned. The same
monitors as last time give the same layout; another set of monitors gets the last layout, with any window or tab
that would open on no screen moved onto one. An old or damaged layout is ignored."""

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QGuiApplication


def arrangement():
    """A short id of the screens' places and sizes, the same for the same monitors in the same order."""
    rects = sorted((s.geometry().x(), s.geometry().y(), s.geometry().width(), s.geometry().height())
                   for s in QGuiApplication.screens())  # fmt: skip
    return ";".join(f"{x},{y},{w}x{h}" for x, y, w, h in rects)


def _b64(data):
    return bytes(data.toBase64()).decode()


def save(window):
    s, k = window.settings, f"area.{window.key}"
    mine = {"geometry": _b64(window.saveGeometry()), "state": _b64(window.saveState())}
    rail = getattr(window, "rail", None)
    if rail is not None:
        mine["pinned"] = rail.pinned
    s.set(f"{k}.geometry", mine["geometry"])  # the last layout: what another arrangement of screens starts from
    s.set(f"{k}.state", mine["state"])
    layouts = s.get(f"{k}.layouts")
    s.set(f"{k}.layouts", {**(layouts if isinstance(layouts, dict) else {}), arrangement(): mine})


def _saved(window):
    s, k = window.settings, f"area.{window.key}"
    layouts = s.get(f"{k}.layouts")
    mine = layouts.get(arrangement()) if isinstance(layouts, dict) else None
    return mine if isinstance(mine, dict) else {"geometry": s.get(f"{k}.geometry"), "state": s.get(f"{k}.state")}


def _off_screen(rect):
    return not any(s.availableGeometry().intersects(rect) for s in QGuiApplication.screens())


def restore(window, geometry=False):
    """The saved layout back; geometry only when the window is new (docks are added after it is built)."""
    from .window import on_screen

    saved = _saved(window)
    if geometry and isinstance(saved.get("geometry"), str):
        window.restoreGeometry(QByteArray.fromBase64(saved["geometry"].encode()))
        on_screen(window)
    if isinstance(saved.get("state"), str):
        window.restoreState(QByteArray.fromBase64(saved["state"].encode()))
    for dock in window.docks.values():
        if dock.isFloating() and _off_screen(dock.frameGeometry()):  # its monitor is gone
            dock.move(window.pos() + window.rect().center() - dock.rect().center())
    rail = getattr(window, "rail", None)
    if rail is not None and isinstance(saved.get("pinned"), bool):
        rail.pin.setChecked(saved["pinned"])
