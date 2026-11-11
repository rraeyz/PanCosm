"""Files and projects of the main window (open, close, save) and its plugins: a mixin of MainWindow moved out of
main_window.py (plans/architecture.md ARC-4.4); texts keep the main window's translation context."""

import json
from pathlib import Path

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QFileDialog, QMessageBox, QTableWidgetItem

from ..engine.project import EXTENSION, Project
from ..io import fits as fitsio
from .files import FITS_FILTER, images_filter
from .messages import translate as message_text

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("MainWindow", "…") calls


class FileActions:
    """Methods of MainWindow (self is the main window)."""

    def new_project_dialog(self):
        path, _ = QFileDialog.getSaveFileName(self, translate("MainWindow", "New project"), "", f"*{EXTENSION}")
        if path:
            self.open_project(Path(path).with_suffix(EXTENSION))

    def open_project_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, translate("MainWindow", "Open project"), "", f"*{EXTENSION}")
        if path:
            self.open_project(Path(path))

    def open_project(self, path: Path):
        try:
            project = Project(path)  # first the new one: a file that is not a project must not close the open one
        except Exception as e:  # not a project file, damaged, no permission
            QMessageBox.warning(
                self, translate("MainWindow", "Cannot open project"), f"{path}\n\n{message_text(str(e))}"
            )
            return False
        if self.engine.project:
            self.engine.project.close()
        self.engine.project = project
        self.project_page.name_label.setText(f"<b>{path}</b>")
        recent = [str(path)] + [p for p in self.settings.get("recent_projects", []) if p != str(path)]
        self.settings.set("recent_projects", recent[:10])
        self._refresh_files()
        self._update_title()
        return True

    def _refresh_files(self):
        self.files_list.clear()
        if not self.engine.project:
            return
        runs = self.engine.project.runs(full=False)  # results stay in the file until a run is selected
        table = self.project_page.runs_table
        table.blockSignals(True)
        table.setRowCount(len(runs))
        for row, r in enumerate(runs):
            for col, val in enumerate((r["step"], r["status"], r["started"], json.dumps(r["params"]))):
                item = QTableWidgetItem(val)
                item.setData(Qt.UserRole, r["id"])
                table.setItem(row, col, item)
        table.blockSignals(False)
        for f in self.engine.project.files():
            self.files_list.addItem(f"{Path(f['path']).name}  [{f['kind']}]")
            self.files_list.item(self.files_list.count() - 1).setData(Qt.UserRole, f["path"])

    def open_fits_dialog(self):
        paths, _ = QFileDialog.getOpenFileNames(self, translate("MainWindow", "Open FITS"), "", images_filter())
        return self.open_many(paths)

    def open_many(self, paths):
        """Open several files at once (as MaxIm DL opens a window for each): all go into the list of open images,
        the first is shown; the others are read only when chosen."""
        if not paths:
            return False
        self.image_page.add_open(paths)
        return self.open_fits(Path(paths[0]), ask=True)

    def close_image(self, everything=False):
        """Take the shown image (or all) out of the list of open images; the files are not touched."""
        page = self.image_page
        if everything:
            for p in page.open_paths():
                page.remove_open(p)
            following = None
        else:
            following = page.remove_open(self.current_path) if self.current_path else None
        if following:
            return self.open_fits(Path(following))
        self.current_path, self.wcs = None, None
        self.viewer.clear()
        page.set_header(None)
        self.header_table.setRowCount(0)
        for act in (self.save_action, self.picture_action, self.solve_action, self.process_menu):
            act.setEnabled(False)
        if hasattr(self, "split_action"):
            self.split_action.setEnabled(False)
        self._update_title()
        return True

    def open_fits(self, path: Path, extension=None, ask=False):
        """Open an image. ask (the user opens a file): a file with several image extensions asks which one, and the
        chosen one is opened as a file of its own, so every tool works on what is shown. Results the application
        writes (stacks with a coverage map, drizzle with a weight map) open on their first image without asking."""
        try:
            from ..io.bayer import fits_copy

            path = fits_copy(path)  # a camera raw file or a picture (phone, JPEG, TIFF): its FITS copy
            choices = fitsio.image_hdus(path)
            if extension is None and ask and len(choices) > 1:
                from PySide6.QtWidgets import QInputDialog

                labels = [c[1] for c in choices]
                label, ok = QInputDialog.getItem(
                    self,
                    translate("MainWindow", "Image extension"),
                    translate("MainWindow", "This file holds several images:"),
                    labels,
                    0,
                    False,
                )
                if not ok:
                    return False
                extension = choices[labels.index(label)][0]
            if extension is not None and choices and extension != choices[0][0]:
                path = fitsio.extract_extension(path, extension)
            data, header, _ = fitsio.read_image(path)
        except Exception as e:  # unreadable or non-image file: tell the user, keep the current image
            QMessageBox.warning(self, translate("MainWindow", "Cannot open file"), f"{path}\n\n{message_text(str(e))}")
            return False
        self.current_path = path
        try:
            from astropy.wcs import WCS

            wcs = WCS(header)
            self.wcs = wcs if wcs.has_celestial else None
        except Exception:
            self.wcs = None
        self.viewer.set_image(data, wcs=self.wcs)
        self.image_page.set_header(header, self.wcs)
        self._show_header(header)
        self.save_action.setEnabled(True)
        self.picture_action.setEnabled(True)
        if getattr(self, "_levels", None) is not None and self._levels.isVisible():
            self._levels.refresh()
        self.solve_action.setEnabled(True)
        self.process_menu.setEnabled(True)
        if hasattr(self, "split_action"):  # a colour camera's raw image (its Bayer pattern in the header)
            from ..io.bayer import pattern_of

            self.split_action.setEnabled(bool(pattern_of(header)))
        self.image_page.add_open([path], current=path)
        if self.engine.project:
            self.engine.project.add_file(path, "image")
            self._refresh_files()
        self._update_title()
        self.show_workspace("image")
        return True

    def _show_header(self, header):
        cards = list(header.cards)
        table = self.header_table
        table.setRowCount(len(cards))
        for row, card in enumerate(cards):
            for col, val in enumerate((card.keyword, str(card.value), card.comment)):
                item = QTableWidgetItem(val)
                item.setToolTip(val if col else "")  # the whole value or comment, however narrow the column
                table.setItem(row, col, item)
        table.resizeColumnsToContents()  # values readable at once; every column can still be dragged wider
        for col, most in ((0, 120), (1, 260)):
            table.setColumnWidth(col, min(table.columnWidth(col), most))

    def save_as_dialog(self):
        path, _ = QFileDialog.getSaveFileName(self, translate("MainWindow", "Save FITS as"), "", FITS_FILTER)
        if path:
            self.save_as(Path(path))

    def save_as(self, destination: Path):
        """Save a copy of the current file through the task queue. Returns the Task."""
        return self.run_step(
            "fits.save_as", {"source": str(self.current_path), "destination": str(destination)}, {"overwrite": True}
        )

    def _fill_plugins_menu(self):
        from ..engine import plugins, steps

        menu = self.plugins_menu
        menu.clear()
        ids = plugins.load_plugins()
        for sid in ids:
            doc = (steps.REGISTRY[sid].func.__doc__ or "").strip().splitlines()
            act = self._action(
                menu, doc[0].rstrip(".") if doc else sid, lambda _=False, i=sid: self.run_plugin(steps.REGISTRY[i])
            )
            act.setToolTip(sid)
        if not ids:
            menu.addAction(translate("MainWindow", "No plugins installed")).setEnabled(False)
        for name, err in plugins.ERRORS.items():
            act = menu.addAction(translate("MainWindow", "Failed to load: {f}").format(f=name))
            act.setToolTip(err)
            act.triggered.connect(
                lambda _=False, e=err: QMessageBox.warning(self, translate("MainWindow", "Plugin error"), e)
            )
        menu.addSeparator()
        self._action(menu, translate("MainWindow", "Install the example plugins"), self.install_example_plugins)
        self._action(menu, translate("MainWindow", "Open plugins folder"), self.open_plugins_folder)
        self._action(menu, translate("MainWindow", "What are plugins?"), lambda: self.show_workspace("guide"))

    def install_example_plugins(self):
        """Copy the three example plugins into the plugins folder; they appear in this menu at once."""
        from ..engine import plugins

        copied = plugins.install_examples()
        plugins.load_plugins()
        text = (
            translate("MainWindow", "Installed: {names}. They are now in the Plugins menu.").format(
                names=", ".join(copied)
            )
            if copied
            else translate("MainWindow", "The example plugins are already installed.")
        )
        self.statusBar().showMessage(text, 10000)
        return copied

    def open_plugins_folder(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        from ..engine.plugins import plugin_dir

        plugin_dir().mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(plugin_dir())))

    def run_plugin(self, step, values=None):
        """Ask for the step's inputs and parameters (or use values) and run it as a task."""
        import json

        from .plugin_dialog import PluginDialog

        if values is None:
            dlg = PluginDialog(step, self)
            if not dlg.exec():
                return None
            values = dlg.values()
        inputs, params = values

        def done(out):
            text = json.dumps(out, indent=1, default=str)
            self.plugin_result = out
            QMessageBox.information(self, step.id, text[:4000] + ("…" if len(text) > 4000 else ""))

        return self.run_step(step.id, inputs, params, on_done=done)
