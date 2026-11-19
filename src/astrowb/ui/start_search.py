"""The start window's "Find anything" (plans/interface.md UI-5 item 6): the command palette over the areas, the
recent files, the guide's topics, the main window's menu actions and every setting. Typing in the start window's
field or Ctrl+K opens it; Enter does what the line says."""

from pathlib import Path

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QAction

from .kit.window import CommandSearch, _plain


def _action(text, slot):
    act = QAction(text)  # kept alive by the palette's list
    act.triggered.connect(lambda _=False: slot())
    return text, act


def commands(main):
    """[(line shown, QAction)] for the palette."""
    from .guide_page import anchors
    from .start_page import visible_areas

    translate = QCoreApplication.translate
    areas_, recent, guide, settings = (
        translate("StartSearch", "Areas"),
        translate("StartSearch", "Recent"),
        translate("StartSearch", "Guide"),
        translate("StartSearch", "Settings"),
    )
    out = [
        _action(f"{areas_} › {name}", lambda k=key: main.open_area(k))
        for key, _s, name, _w in visible_areas(main.settings)
    ]
    for kind, path in main.recent_work():
        if Path(path).exists():
            out.append(_action(f"{recent} › {Path(path).name}", lambda k=kind, p=path: main._resume(k, p)))
    for anchor, (chapter, name, _md) in anchors(main.settings.get("ui.language", "en")).items():
        out.append(_action(f"{guide} › {chapter} › {name}", lambda a=anchor: main._help_for(a)))
    seen = set()

    def walk(menu, path):
        for act in menu.actions():
            if act.menu() is not None:
                walk(act.menu(), [*path, _plain(act.text())])
            elif act.text() and not act.isSeparator() and act not in seen:
                seen.add(act)
                out.append((" › ".join([*path, _plain(act.text())]), act))

    for top in main.menuBar().actions():
        if top.menu() is not None:
            walk(top.menu(), [_plain(top.text())])
    from .settings_window import SettingsWindow

    win = SettingsWindow(main)  # only to read its rows; never shown
    for category, row, _note, _words in win.rows:
        label = row.label.text()
        if label:
            line = f"{settings} › {win.categories.item(category).text()} › {label}"
            out.append(_action(line, lambda c=category, t=label: _open_setting(main, c, t)))
    win.deleteLater()
    return out


def _open_setting(main, category, label):
    win = main.show_settings()
    win.categories.setCurrentRow(category)
    win.search.setText(label)


def open_palette(main, text=""):
    dialog = CommandSearch(commands(main), main)
    if text:
        dialog.search.setText(text)
    dialog.move(main.mapToGlobal(main.rect().center()) - dialog.rect().center())
    dialog.show()
    dialog.search.setFocus()
    return dialog
