"""The Help menu, with the installation check and the GPU check: each check runs as a task and shows its report
(ARC-10). Texts keep the main window's translation context ("MainWindow")."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QFont, QKeySequence
from PySide6.QtWidgets import QMessageBox

from ..brand import BRAND
from .kit.widgets import bar_menu


def add_menu(win):
    h = bar_menu(win.menuBar(), QCoreApplication.translate("MainWindow", "&Help"))
    win._action(h, QCoreApplication.translate("MainWindow", "Report a problem…"), win.report_problem)
    win._action(
        h,
        QCoreApplication.translate("MainWindow", "Training &guide"),
        lambda: win.show_workspace("guide"),
        QKeySequence.HelpContents,
    )
    win.tour_action = win._action(h, QCoreApplication.translate("MainWindow", "Quick &tour"), win.start_tour)
    win._action(h, QCoreApplication.translate("MainWindow", "&Practice data for a first night…"), win.practice_data)
    win._action(
        h,
        QCoreApplication.translate("MainWindow", "Check the &installation and internet services"),
        lambda: installation(win),
    )
    win._action(h, QCoreApplication.translate("MainWindow", "Check the &GPU…"), lambda: gpu(win))
    win.update_action = win._action(
        h, QCoreApplication.translate("MainWindow", "Check for &updates…"), win.check_updates
    )
    about = QCoreApplication.translate("MainWindow", "&About {app}").format(app=BRAND.display_name)
    win.about_action = win._action(h, about, win.about)
    return h


def installation(win):
    """Every part of the installation and every web service (SIMBAD, VizieR, MAST, ...) in one report: what to
    send when something does not work."""

    def done(out):
        title = QCoreApplication.translate("MainWindow", "Installation and internet services")
        box = QMessageBox(QMessageBox.Information, title, "", parent=win)
        box.setText(
            QCoreApplication.translate("MainWindow", "Everything works.")
            if out["ok"]
            else QCoreApplication.translate(
                "MainWindow",
                "Some checks failed (see below). A failing web service is often the network or the service.",
            )
        )
        box.setDetailedText(out["report"])
        box.exec()

    text = QCoreApplication.translate("MainWindow", "Checking the installation and the internet services…")
    win.statusBar().showMessage(text, 60000)
    return win.run_step("app.check", {}, {}, on_done=done)


def gpu(win):
    """Every GPU job against its CPU twin: times and whether the results agree (about a minute)."""

    def done(out):
        box = QMessageBox(
            QMessageBox.Information, QCoreApplication.translate("MainWindow", "GPU check"), "", parent=win
        )
        saved = QCoreApplication.translate(
            "MainWindow", "The report is also saved in {path} (Report a problem includes it)."
        )
        box.setText(saved.format(path=out["path"]))
        box.setDetailedText(out["report"])
        box.setFont(QFont("monospace"))
        box.exec()

    text = QCoreApplication.translate("MainWindow", "Checking the GPU: every GPU job against the CPU (about a minute)…")
    win.statusBar().showMessage(text, 120000)
    return win.run_step("app.check_gpu", {}, {}, on_done=done)
