"""The start window's Practice data menu (plans/interface.md UI-5 item 2): the practice sets that sample.night
writes into one folder (ARC-21, `sampledata`), each opened in its area window with its file."""

from pathlib import Path

from PySide6.QtCore import QT_TRANSLATE_NOOP, QCoreApplication
from PySide6.QtWidgets import QFileDialog, QMenu

translate = QCoreApplication.translate

SETS = (  # (key, name, area, file or folder in the practice folder)
    ("night", QT_TRANSLATE_NOOP("PracticeSets", "An eclipsing binary's night (raw frames)"), "calibrate", "raw"),
    ("transit", QT_TRANSLATE_NOOP("PracticeSets", "A transit night (raw frames)"), "calibrate", "transit/raw"),
    ("pulsator", QT_TRANSLATE_NOOP("PracticeSets", "A pulsating star's light curve"), "timeseries", "pulsator.csv"),
    ("minima", QT_TRANSLATE_NOOP("PracticeSets", "Minima with a third body"), "oc", "minima.txt"),
    ("sb2", QT_TRANSLATE_NOOP("PracticeSets", "A double-lined binary's velocities"), "spectroscopy", "sb2.csv"),
    ("longslit", QT_TRANSLATE_NOOP("PracticeSets", "A long-slit spectrum"), "spectroscopy", "slit_science.fits"),
)


def menu(parent, settings, emit):
    """Every set with the Guide (the old single action), then one entry per set whose area is shown."""
    from .start_page import visible_areas

    shown = {key for key, *_ in visible_areas(settings)}
    out = QMenu(parent)
    out.addAction(translate("PracticeSets", "Every set, with the Guide's first night"), lambda: emit("practice_data"))
    out.addSeparator()
    for key, name, area, _file in SETS:
        if area in shown:
            out.addAction(translate("PracticeSets", name), lambda k=key: emit("practice:" + k))
    return out


def choose(main, key, folder=None):
    """Write the practice data into a folder, then open the set in its window."""
    folder = folder or QFileDialog.getExistingDirectory(main, translate("MainWindow", "Folder for the practice data"))
    if folder:
        main.practice_data(folder, then=lambda: open_set(main, key, folder))


def open_set(main, key, folder):
    _key, _name, area, name = next(s for s in SETS if s[0] == key)
    path = str(Path(folder) / name)
    if key == "sb2":  # a table of velocities, not a spectrum: the Radial velocity tab reads it
        from . import velocity_table

        main.open_area(area)
        page = main.spectro_page
        page.tabs.setCurrentWidget(page.velocity_tab)
        velocity_table.open_dialog(page.velocity_tab, path)
        return
    main._resume(area, path)  # as a Continue card: the window opened with the file
