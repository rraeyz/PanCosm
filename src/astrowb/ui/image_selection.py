"""Per-file actions on the files selected in the Images window's strip (UI-16.10): each loops the single-file action
(Close image, Save FITS as, Blink images) over the selection; right-click the strip."""

from pathlib import Path

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QFileDialog, QMenu

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("ImageWindow", "…") calls


def close_selected(page, main):
    picked = page.selected_paths()
    for p in picked:
        if str(p) != str(main.current_path):
            page.remove_open(p)
    if main.current_path and str(main.current_path) in map(str, picked):
        main.close_image()  # the shown one last: it opens its neighbour
    return picked


def save_selected(page, main, folder=None):
    """Save a copy of each selected file into a folder (names kept; a repeated name gets a number); the tasks."""
    picked = page.selected_paths()
    folder = folder or QFileDialog.getExistingDirectory(page, translate("ImageWindow", "Save the selected images in…"))
    if not picked or not folder:
        return []
    tasks, used = [], set()
    for p in picked:
        name, n = Path(p).name, 1
        while name in used:
            n += 1
            name = f"{n}_{Path(p).name}"
        used.add(name)
        tasks.append(
            main.run_step(
                "fits.save_as", {"source": str(p), "destination": str(Path(folder) / name)}, {"overwrite": True}
            )
        )
    return tasks


def blink_selected(page, main):
    picked = page.selected_paths()
    if len(picked) < 2:
        return None
    dlg = main.blink_dialog()
    dlg.set_images(picked)
    return dlg


def add_selection_menu(page, main):
    def show(pos):
        n = len(page.selected_paths())
        menu = QMenu(page.open_list)
        menu.addAction(translate("ImageWindow", "Close the selected images"), lambda: close_selected(page, main))
        menu.addAction(translate("ImageWindow", "Save the selected images in…"), lambda: save_selected(page, main))
        menu.addAction(translate("ImageWindow", "Blink the selected images…"), lambda: blink_selected(page, main))
        for act in menu.actions():
            act.setEnabled(n > 0)
        menu.actions()[2].setEnabled(n > 1)
        menu.popup(page.open_list.viewport().mapToGlobal(pos))
        page.selection_menu = menu

    page.open_list.setContextMenuPolicy(Qt.CustomContextMenu)
    page.open_list.customContextMenuRequested.connect(show)
