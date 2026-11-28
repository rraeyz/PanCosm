"""UI-5: every area of the start window opened by keyboard only (Tab and Enter), and the Practice data menu
opening one set in its area window."""

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from astrowb.settings import Settings


def _main(qtbot, tmp_path):
    from astrowb.ui.main_window import MainWindow

    main = MainWindow(Settings(tmp_path / "s"))
    qtbot.addWidget(main)
    main.resize(1366, 768)
    main.show()
    qtbot.waitExposed(main)
    return main


def test_every_area_opens_by_keyboard_only(qtbot, tmp_path):
    main = _main(qtbot, tmp_path)
    try:
        page = main.start_page
        for block in page.blocks:
            key = block.objectName().removeprefix("start_")
            main.activateWindow()
            qtbot.waitUntil(lambda: QApplication.activeWindow() is main)
            page.buttons[0].setFocus()  # the start of the tab order, as on opening the window
            for _ in range(60):  # Tab until the card has the focus; no click anywhere
                if QApplication.focusWidget() is block:
                    break
                QTest.keyClick(QApplication.focusWidget(), Qt.Key_Tab)
            assert QApplication.focusWidget() is block, key
            QTest.keyClick(block, Qt.Key_Return)
            assert key in main.area_windows or main.current_workspace() == key, key
    finally:
        main.engine.shutdown()


def test_practice_menu_opens_a_set_in_its_window(qtbot, tmp_path):
    from astrowb import sampledata
    from astrowb.ui import practice_sets

    main = _main(qtbot, tmp_path)
    try:
        button = main.start_page.findChild(type(main.start_page.buttons[0]), "start_practice_data")
        names = [a.text() for a in button.menu().actions() if a.text()]
        assert names[0] == "Every set, with the Guide's first night"
        assert "A pulsating star's light curve" in names and "Minima with a third body" in names
        folder = tmp_path / "practice"
        folder.mkdir()
        sampledata.minima(folder)  # the step writes every set; here only the one opened
        main.practice_data = lambda f, then=None: then()
        practice_sets.choose(main, "minima", str(folder))
        assert "oc" in main.area_windows
        assert main.settings.get("area.oc.recent")[0] == str(folder / "minima.txt")
        sampledata.sb2(folder)
        practice_sets.open_set(main, "sb2", str(folder))
        page = main.spectro_page
        assert page.tabs.currentWidget() is page.velocity_tab and len(page.velocity_tab.rvs) == 30
    finally:
        main.engine.shutdown()
