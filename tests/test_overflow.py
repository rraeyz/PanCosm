"""User feedback UF-9, UF-10: opening a folded section pushed the window's content past its right edge (Calibration
windowed, Photometry's Measure stage even full screen). Every area window at 1366 × 768, every fold opened: nothing
may be wider than the window."""

import pytest

from astrowb.settings import Settings


@pytest.fixture(params=["en", "tr", "de"])
def main(qtbot, tmp_path, request):
    from PySide6.QtWidgets import QApplication

    from astrowb.ui import i18n, theme
    from astrowb.ui.main_window import MainWindow

    app = QApplication.instance()
    was = app.font()
    theme.apply(app)  # the program's own style and bundled font, as it starts: the same letters on every system
    translators = i18n.install(app, request.param) if request.param != "en" else []
    settings = Settings(tmp_path)
    settings.set("ui.language", request.param)
    win = MainWindow(settings)
    qtbot.addWidget(win)
    win.show()
    yield win
    win.engine.shutdown()
    for t in translators:
        app.removeTranslator(t)
    app.setFont(was)


def test_opened_folds_fit_the_window(main):
    from PySide6.QtWidgets import QApplication

    from astrowb.ui.kit.widgets import Collapsible

    too_wide = []
    for key in main.WINDOWED:
        area = main.open_area(key) or main
        area.resize(1366, 768)
        area.show()
        for fold in area.findChildren(Collapsible):
            fold.set_expanded(True)
        for stage in getattr(area, "stage_panels", None) or [None]:  # every stage of a staged window in turn
            if stage is not None:
                area.show_stage(stage)
            QApplication.processEvents()
            too_wide += _overflows(area, f"{key}/{stage}" if stage else key)
    assert not too_wide, too_wide


def _overflows(area, where):
    from PySide6.QtWidgets import QScrollArea

    too_wide = []
    if area.minimumSizeHint().width() > 1366:
        too_wide.append(f"{where}: window needs {area.minimumSizeHint().width()} px")
    for scroll in area.findChildren(QScrollArea):
        bar = scroll.horizontalScrollBar()
        if scroll.isVisible() and bar.maximum() > 0:
            too_wide.append(f"{where}: {type(scroll.widget()).__name__} scrolls sideways by {bar.maximum()} px")
        inner = scroll.widget()
        need = inner.minimumSizeHint().width() if inner is not None else 0
        if scroll.isVisible() and inner is not None and need > scroll.viewport().width() + 2:
            too_wide.append(f"{where}: {type(inner).__name__} needs {need} px in {scroll.viewport().width()} px")
    return too_wide
