"""UI-6's acceptance: every window opened in a fresh profile, every plot and image view it shows says what will
appear there (data or words, never a blank rectangle)."""

import numpy as np
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
    from astrowb.ui.plot.view import PlotView
    from astrowb.ui.viewer import ImageViewer

    blank = []
    for key in main.WINDOWED:
        area = main.open_area(key) or main
        area.show()
        QApplication.processEvents()
        for view in area.findChildren(ImageViewer):
            if view.isVisible() and view.data is None and not view.empty_hint.strip():
                blank.append(f"{key}: image view {view.objectName() or type(view.parent()).__name__}")
        for plot in area.findChildren(PlotView):
            if plot.isVisible() and plot.is_empty() and not (plot.hint.isVisible() and plot.hint.text().strip()):
                blank.append(f"{key}: plot in {type(plot.parent()).__name__}")
        for plot in area.findChildren(PlotCanvas):
            drawn = any(ax.has_data() for ax in plot.figure.axes)
            if plot.isVisible() and not drawn and not (plot.hint.isVisible() and plot.hint.text().strip()):
                blank.append(f"{key}: plot in {type(plot.parent()).__name__}")
    assert not blank, blank


def test_every_shown_plot_has_its_own_words(main):
    """UI-6's table of views (ui/empty_texts.py): a plot in sight names what will appear there and what to do, not the
    general "Nothing to show yet"."""
    from PySide6.QtWidgets import QApplication

    from astrowb.ui.kit.widgets import PlotCanvas
    from astrowb.ui.plot.view import PlotView

    general = []
    for key in main.WINDOWED:
        area = main.open_area(key) or main
        area.show()
        QApplication.processEvents()
        for plot in [*area.findChildren(PlotView), *area.findChildren(PlotCanvas)]:
            if plot.isVisible() and plot._empty_text.startswith("Nothing to show yet"):
                general.append(f"{key}: plot in {type(plot.parent()).__name__}")
    assert not general, general


def test_a_plot_box_with_a_key_says_its_words_then_data_then_busy(qtbot):
    """The empty, loading and data states of one plot made by plot_box with a key of the table."""
    from astrowb.ui.empty_texts import empty_text
    from astrowb.ui.plot.spec import AxisSpec, FigureSpec, PanelSpec, SeriesSpec
    from astrowb.ui.plot.toolbar import plot_box

    box, plot = plot_box(None, "oc")
    qtbot.addWidget(box)
    box.resize(500, 300)
    box.show()
    qtbot.wait(20)  # the toolbar's tab order is set once shown (kit/focus)
    assert plot.is_empty() and plot.hint.isVisible() and plot.hint.text() == empty_text("oc")
    plot.set_busy("Working: O−C — 40 %")
    assert plot.hint.text() == "Working: O−C — 40 %"
    plot.set_busy(None)
    assert plot.hint.text() == empty_text("oc")
    plot.set_figure(
        FigureSpec(
            [
                PanelSpec(
                    AxisSpec("E"), AxisSpec("O−C"), [SeriesSpec("minima", np.array([1.0, 2.0]), np.array([0.1, 0.2]))]
                )
            ]
        )
    )
    assert not plot.is_empty() and not plot.hint.isVisible()
    with pytest.raises(KeyError):
        empty_text("no such plot")
