"""The Tools menu every area window shares (plans/interface.md UI-4 item 3: File, Edit, View, <area menus>, Tools,
Window, Help): the tools that belong to no one area, each a dialog of its own."""

from PySide6.QtCore import QCoreApplication

from .widgets import bar_menu

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("AreaWindow", "…") calls


def _open(win, dialog_class):
    win.tool_dialog = dialog_class(win.settings, win)  # kept: a dialog without a reference is collected
    win.tool_dialog.show()
    return win.tool_dialog


def _converter():
    from ..converter_dialog import ConverterDialog

    return ConverterDialog


def _camera():
    from ..camera_dialog import CameraDialog

    return CameraDialog


def _headers():
    from ..headers_dialog import HeadersDialog

    return HeadersDialog


def retitle(win):
    """The Alt key of Tools: its first letter no other menu of this window's bar has (the areas' menus differ, and
    every letter of "Tools" is some area's); none when all are taken. Called again when the area adds menus."""
    import re

    bar, act = win.menuBar(), win.tools_menu.menuAction()
    title = act.text().replace("&", "")
    taken = {m.group(1).lower() for a in bar.actions() if a is not act for m in [re.search(r"&(\w)", a.text())] if m}
    i = next((i for i, ch in enumerate(title) if ch.isalnum() and ch.lower() not in taken), None)
    act.setText(title if i is None else title[:i] + "&" + title[i:])


def build(win, bar):
    """The menu, after the area's own menus and before Window (the area's later menus go before it too)."""
    menu = win.tools_menu = bar_menu(bar, translate("AreaWindow", "Tools"))
    retitle(win)
    tools = (
        (translate("AreaWindow", "Time and coordinate converter…"), _converter,
         translate("AreaWindow", "A time in any standard (JD, HJD, BJD) into the others, with the altitude, airmass "
                                 "and barycentric correction of a target")),
        (translate("MainWindow", "Measure the camera…"), _camera,
         translate("AreaWindow", "Gain and read noise from two flats and two biases")),
        (translate("MainWindow", "Edit the headers of many files…"), _headers,
         translate("AreaWindow", "Set, rename or delete header keywords over many files at once")),
    )  # fmt: skip
    for text, which, tip in tools:
        win._action(menu, text, lambda w=which: _open(win, w()), tip=tip)
    win.set_icons(dict(zip(menu.actions(), ("converter", "camera_measure", "edit_headers"), strict=True)))
    return menu
