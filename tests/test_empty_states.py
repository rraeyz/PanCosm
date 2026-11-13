"""UI-6's acceptance: every window opened in a fresh profile, every plot and image view it shows says what will
appear there (data or words, never a blank rectangle)."""

import pytest

from astrowb.settings import Settings


@pytest.fixture
def main(qtbot, tmp_path):
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    win.show()
    yield win
    win.engine.shutdown()


def test_every_view_says_what_will_appear(main, qtbot):
    from PySide6.QtWidgets import QApplication

    from astrowb.ui.kit.widgets import PlotCanvas
    from astrowb.ui.viewer import ImageViewer

    blank = []
    for key in main.WINDOWED:
        area = main.open_area(key) or main
        area.show()
        QApplication.processEvents()
        for view in area.findChildren(ImageViewer):
            if view.isVisible() and view.data is None and not view.empty_hint.strip():
                blank.append(f"{key}: image view {view.objectName() or type(view.parent()).__name__}")
        for plot in area.findChildren(PlotCanvas):
            drawn = any(ax.has_data() for ax in plot.figure.axes)
            if plot.isVisible() and not drawn and not (plot.hint.isVisible() and plot.hint.text().strip()):
                blank.append(f"{key}: plot in {type(plot.parent()).__name__}")
    assert not blank, blank
