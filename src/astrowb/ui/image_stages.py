"""The Images window on the anatomy (plans/interface.md UI-16.10): a viewer, not a workflow, so no rail. The image with
its tool rows is the main view, the open images are the file strip at the left (F9), the header, information and graph
tabs are the inspector at the right (F10). The page keeps the state and the logic, unseen."""

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QScrollArea, QSplitter

from .image_inspector import add_inspector_tabs, empty_state, file_strip
from .kit.focus import read_in_order

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("ImageWindow", "…") calls


def image_anatomy(main, win, page):
    page.setParent(win)  # before the old frame goes: the page owns the viewer, the list and the tabs
    left, tabs = page.split.widget(0), page.split.widget(1)
    strip = page.open_list.parentWidget()
    assert isinstance(strip, QSplitter)  # the list sat beside the viewer; the strip takes its place
    page.open_list.setMinimumWidth(150)
    page.open_list.setMaximumWidth(260)
    win.set_main(left)
    page.hide()
    add_inspector_tabs(page)
    win.set_inspector(tabs)
    dock = win._dock("files", translate("ImageWindow", "Open images"), file_strip(page), Qt.LeftDockWidgetArea)
    dock.hide()
    empty = empty_state(main)

    def follow(_=None):  # one image needs no strip, as before; no image shows what to do
        dock.setVisible(page.open_list.count() > 1)
        win.set_empty_state(empty if page.viewer.data is None else None)
        page.filter_line.textChanged.emit(page.filter_line.text())
        page.refresh_inspector()

    follow()

    for name in ("add_open", "remove_open"):
        method = getattr(page, name)

        def wrapped(*args, _m=method, **kw):
            out = _m(*args, **kw)
            follow()
            return out

        setattr(page, name, wrapped)
    frame = QScrollArea(win)  # the page's place in main._frames (Basic / Expert, size checks): unseen
    frame.setWidget(page)
    frame.hide()
    main._frames[page] = frame
    win._docks_added()
    read_in_order(left, page.open_list, tabs)  # Tab follows the screen: image with its tools, strip, inspector


def image(main, page, win):
    """The area_menus builder for the Images window (looked up by the area key)."""
    image_anatomy(main, win, page)
