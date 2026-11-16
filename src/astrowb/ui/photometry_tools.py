"""The Images window's image tools on the Photometry window's image (plans/interface.md UI-16.1): Star (counts, FWHM,
HFD, background, S/N, profile), Area (rectangle statistics) and Line (profile along a line). The measuring code is the
Images page's own: an ImagePage is built unseen and pointed at Photometry's viewer, so nothing is measured twice. The
default tool (Move) leaves a click to Photometry, which marks stars; only the Star tool measures instead."""

from PySide6.QtCore import QCoreApplication, Qt

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("PhotometryTools", "…") calls


def attach(win, page):
    from .image_page import ImagePage

    tools = page.image_tools = ImagePage(win)
    tools.hide()
    tools.viewer.deleteLater()  # the page built its own viewer; Photometry's is the one measured
    tools.viewer = page.viewer
    tools.set_floating(False)  # the results in tabs (a dock), not small windows over the image
    tools.tabs.removeTab(0)  # the header is for editing keywords: not here
    header = {}

    def refresh(*_):
        """The frame shown: its header (gain, exposure, saturation) and, on the first frame, the field's solution."""
        path = page.images[page.shown] if page.images and page.shown < len(page.images) else None
        if path not in header:
            try:
                from ..calibration.masters import load

                header[path] = load(path)[1]
            except (OSError, ValueError, TypeError):  # a frame that is gone: counts without gain
                header[path] = None
        tools.header = header[path]
        tools.wcs = page._field_wcs() if page.field and page.shown == 0 else None

    v = page.viewer
    for signal, slot in (
        (v.clicked, tools._clicked),
        (v.region_selected, tools.measure_area),
        (v.line_selected, tools.measure_line),
        (v.star_key, tools.measure_star),
    ):
        signal.connect(refresh)  # connected first: runs before the measurement
        signal.connect(slot)
    tools.whole_button.clicked.connect(refresh)
    bars = [tools.split.widget(0).layout().itemAt(i).widget() for i in (0, 1)]
    for i, bar in enumerate(bars):  # the tool buttons and their settings row, in the window's toolbar area
        bar.setObjectName(f"image_tools_{i}")
        win.addToolBar(Qt.TopToolBarArea, bar)
    inspector = win.docks["inspector"]
    dock = win._dock("measure", translate("PhotometryTools", "Measurements"), tools.tabs, Qt.RightDockWidgetArea)
    win.splitDockWidget(inspector, dock, Qt.Vertical)  # one under the other
    dock.hide()
    show = tools._show_tool
    tools._show_tool = lambda key: (show(key), dock.show(), dock.raise_())[0]  # a measurement brings its numbers up
    win._docks_added()
    from .kit.focus import read_in_order

    read_in_order(
        win.toolbar, *bars, win.docks["stages"], page.viewer, inspector, tools.tabs, win.docks["results"]
    )  # Tab follows the screen
