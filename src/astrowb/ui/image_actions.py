"""The main window's image commands (View, Image and right-click menus: processing, colour, astrometry, stacking,
pictures, levels, blink), a mixin of MainWindow moved out of main_window.py (plans/architecture.md ARC-4.4).
Texts keep the main window's translation context."""

from pathlib import Path

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QFileDialog, QLabel, QMessageBox

from ..io import fits as fitsio
from .files import FITS_FILTER, images_filter

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("MainWindow", "…") calls


class ImageActions:
    """Methods of MainWindow (self is the main window)."""

    def image_menu(self, x, y):
        """Right click on the image: what can be done with the star or place under the mouse."""
        from PySide6.QtWidgets import QMenu

        menu = QMenu(self)
        page = self.image_page
        self._action(
            menu,
            translate("MainWindow", "Send the open images to Photometry"),
            lambda: self.send_to_photometry(page.open_paths() or [str(self.current_path)]),
        )
        menu.addSeparator()
        self._action(menu, translate("MainWindow", "Measure this star"), lambda: page.measure_star(x, y))
        self._action(
            menu,
            translate("MainWindow", "Photometry: this star as the target"),
            lambda: self.photometry_from_image(x, y),
        )
        comp = self._action(
            menu,
            translate("MainWindow", "Photometry: add as a comparison star"),
            lambda: self.photometry_from_image(x, y, True),
        )
        phot = self.__dict__.get("photometry_page")
        comp.setEnabled(bool(phot and phot.images and phot.target and str(phot.images[0]) == str(self.current_path)))
        menu.addSeparator()
        self._action(menu, translate("MainWindow", "Copy the position"), lambda: self._copy_position(x, y))
        simbad = self._action(menu, translate("MainWindow", "Look up in SIMBAD"), lambda: self._simbad(x, y))
        simbad.setEnabled(self.wcs is not None)
        menu.addSeparator()
        self._action(
            menu,
            translate("MainWindow", "Centre the view here"),
            lambda: self.viewer.centerOn(x + 0.5, page.viewer.data.shape[0] - 0.5 - y),
        )
        menu.addAction(self.fit_action)
        self._action(menu, translate("MainWindow", "Statistics of the whole image"), page.measure_whole)
        return menu

    def _sky(self, x, y):
        return self.wcs.pixel_to_world(x, y) if self.wcs is not None else None

    def _copy_position(self, x, y):
        from PySide6.QtWidgets import QApplication

        text = f"x={x + 1:.1f} y={y + 1:.1f}"  # FITS convention, as in the status bar
        sky = self._sky(x, y)
        if sky is not None:
            text += f"  {sky.to_string('hmsdms', sep=':', precision=2)}  ({sky.ra.deg:.6f} {sky.dec.deg:+.6f})"
        QApplication.clipboard().setText(text)
        self.statusBar().showMessage(text, 8000)
        return text

    def _simbad(self, x, y):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        sky = self._sky(x, y)
        url = QUrl(
            "https://simbad.cds.unistra.fr/simbad/sim-coo?Coord="
            f"{sky.ra.deg:.6f}%20{sky.dec.deg:+.6f}&Radius=10&Radius.unit=arcsec"
        )
        QDesktopServices.openUrl(url)
        return url

    def save_header_changes(self, set_cards, delete, destination=None):
        """A copy of the current file with the edited header, opened when written."""
        if self.current_path is None:
            return None
        if destination is None:
            suggestion = str(self.current_path.with_name(self.current_path.stem + "_hdr.fits"))
            destination, _ = QFileDialog.getSaveFileName(
                self, translate("MainWindow", "Save FITS as"), suggestion, FITS_FILTER
            )
        if not destination:
            return None
        return self.run_step(
            "fits.save_as",
            {"source": str(self.current_path), "destination": str(destination)},
            {"overwrite": True, "set_cards": set_cards, "delete": delete},
            on_done=lambda out: self.open_fits(Path(out["destination"])),
        )

    def process_dialog(self, op):
        """Ask for the operation's settings (if any) and run it on the current image."""
        from PySide6.QtWidgets import QInputDialog

        if isinstance(op, tuple):
            return self.process_image(*op)
        if op == "pixel_math":
            others, _ = QFileDialog.getOpenFileNames(
                self, translate("MainWindow", "Other images, named B, C, … (optional)"), "", images_filter()
            )
            expr, ok = QInputDialog.getText(
                self,
                translate("MainWindow", "Pixel math"),
                translate("MainWindow", "Expression (A is this image), e.g. A - 0.95 * B:"),
            )
            from ..io.bayer import fits_paths

            return self.process_image("pixel_math", {"expression": expr}, fits_paths(others)) if ok and expr else None
        if op == "crop":
            text, ok = QInputDialog.getText(
                self,
                translate("MainWindow", "Crop"),
                translate("MainWindow", "x0 x1 y0 y1 (pixels, 0-based, end excluded):"),
            )
            try:
                x0, x1, y0, y1 = (int(v) for v in text.replace(",", " ").split())
            except ValueError:
                return None
            return self.process_image("crop", {"x0": x0, "x1": x1, "y0": y0, "y1": y1}) if ok else None
        if op == "rotate":
            angle, ok = QInputDialog.getDouble(
                self,
                translate("MainWindow", "Rotate"),
                translate("MainWindow", "Angle (degrees, counter-clockwise):"),
                0.0,
                -360.0,
                360.0,
                3,
            )
            return self.process_image("rotate", {"angle": angle}) if ok else None
        if op == "histogram_match":
            ref, _ = QFileDialog.getOpenFileName(self, translate("MainWindow", "Reference image"), "", images_filter())
            from ..io.bayer import fits_copy

            return self.process_image("histogram_match", {"reference": str(fits_copy(ref))}) if ref else None
        if op in ("kernel", "deconvolve"):
            return self._ask_kernel_or_deconvolve(op)
        prompts = {
            "resample": (translate("MainWindow", "Factor (2: twice as many pixels across, 0.5: half):"), "factor", 2.0),
            "gaussian": (translate("MainWindow", "Sigma (pixels):"), "sigma", 1.5),
            "median": (translate("MainWindow", "Box size (pixels, odd):"), "size", 3),
            "unsharp": (translate("MainWindow", "Sigma (pixels):"), "sigma", 2.0),
            "background": (translate("MainWindow", "Box size (pixels):"), "box", 64),
        }
        label, key, default = prompts[op]
        value, ok = QInputDialog.getDouble(self, translate("MainWindow", "Process"), label, default, 0.01, 10000, 2)
        if not ok:
            return None
        return self.process_image(op, {key: int(value) if key in ("size", "box") else value})

    def _ask_kernel_or_deconvolve(self, op):
        """The settings of a kernel filter or a deconvolution, then the operation."""
        from PySide6.QtWidgets import QInputDialog

        if op == "kernel":
            kinds = {
                translate("MainWindow", "Low pass (smooth)"): "lowpass",
                translate("MainWindow", "High pass (sharpen)"): "highpass",
                translate("MainWindow", "Laplacian"): "laplacian",
                translate("MainWindow", "Edges (Sobel)"): "sobel",
                translate("MainWindow", "Vertical edges"): "edge_x",
                translate("MainWindow", "Horizontal edges"): "edge_y",
            }
            name, ok = QInputDialog.getItem(
                self,
                translate("MainWindow", "Kernel filter"),
                translate("MainWindow", "Filter:"),
                list(kinds),
                0,
                False,
            )
            return self.process_image("kernel", {"kind": kinds[name]}) if ok else None
        if op == "deconvolve":
            fwhm, ok = QInputDialog.getDouble(
                self,
                translate("MainWindow", "Deconvolution"),
                translate("MainWindow", "Star FWHM (pixels; measure it with the Star tool):"),
                3.0,
                0.5,
                50,
                2,
            )
            if not ok:
                return None
            n, ok = QInputDialog.getInt(
                self, translate("MainWindow", "Deconvolution"), translate("MainWindow", "Iterations:"), 20, 1, 500
            )
            return self.process_image("deconvolve", {"fwhm": fwhm, "iterations": n}) if ok else None

    def process_image(self, op, args=None, others=None):
        """Run an image operation on the current file, or on every open image (Process -> Apply to all open
        images: each processed copy takes the place of its original in the list); the result opens when written."""
        if getattr(self, "current_path", None) is None:
            return None
        every = self.apply_all_action.isChecked()
        tasks = []
        for path in self.image_page.open_paths() if every else [str(self.current_path)]:
            inputs = {"image": path, "operation": op}
            if others:
                inputs["others"] = list(others)
            tasks.append(
                self.run_step(
                    "image.process", inputs, {"args": args or {}}, on_done=lambda out, p=path: self._processed(p, out)
                )
            )
        return tasks if every else tasks[0]

    def _processed(self, source, out):
        if self.apply_all_action.isChecked():
            self.image_page.replace_open(source, out["image"])
        if source == str(self.current_path) or not self.apply_all_action.isChecked():
            # Ctrl+Z shows the image before the operation again (the processed copy stays on disk)
            self.image_page.edit(translate("MainWindow", "image operation"), self.open_fits, Path(out["image"]))

    def colour_dialog(self, paths=None, output=None):
        """Red, green and blue frames -> a colour PNG (aligned, Lupton asinh stretch), shown when ready."""
        if paths is None:
            paths = []
            for label in (
                translate("MainWindow", "Red frame"),
                translate("MainWindow", "Green frame"),
                translate("MainWindow", "Blue frame"),
            ):
                path, _ = QFileDialog.getOpenFileName(self, label, "", images_filter())
                if not path:
                    return None
                paths.append(path)
            output, _ = QFileDialog.getSaveFileName(
                self, translate("MainWindow", "Colour image"), "colour.png", "PNG (*.png)"
            )
            if not output:
                return None
        from ..io.bayer import fits_paths

        inputs = dict(zip(("red", "green", "blue"), fits_paths(paths), strict=True)) | {"output": output}
        return self.run_step("image.rgb", inputs, {}, on_done=lambda out: self.show_picture(out["rgb"]))

    def coefficients_dialog(self):
        from .coefficients_dialog import CoefficientsDialog

        lc = getattr(self.photometry_page, "lc_raw", None) if "photometry_page" in self.__dict__ else None
        dlg = CoefficientsDialog(lc, self)
        dlg.transform_requested.connect(
            lambda a, b, params: self.run_step(
                "photometry.transformation", {"image_a": a, "image_b": b}, params, on_done=dlg.show_transformation
            )
        )
        dlg.open()
        self.coefficients = dlg
        return dlg

    def moving_dialog(self):
        from .moving_dialog import MovingObjectDialog

        dlg = MovingObjectDialog(self.settings, self)
        dlg.measure_requested.connect(
            lambda images, first, last: self.run_step(
                "astrometry.moving",
                {"images": images, "first_xy": first, "last_xy": last},
                {},
                on_done=lambda out: dlg.show_positions(out["positions"], out.get("unsolved", ())),
            )
        )
        dlg.open()
        self.astrometry_dialog = dlg
        return dlg

    def show_picture(self, path):
        from PySide6.QtGui import QPixmap
        from PySide6.QtWidgets import QDialog, QScrollArea, QVBoxLayout

        dlg = QDialog(self)
        dlg.setWindowTitle(Path(path).name)
        label = QLabel(dlg)
        label.setPixmap(QPixmap(str(path)))
        area = QScrollArea(dlg)
        area.setWidget(label)
        QVBoxLayout(dlg).addWidget(area)
        dlg.resize(900, 700)
        dlg.open()
        self.picture_dialog = dlg
        return dlg

    def levels_dialog(self):
        from .levels_dialog import LevelsDialog

        if getattr(self, "_levels", None) is None:
            self._levels = LevelsDialog(self.viewer, self)
        self._levels.refresh()
        self._levels.show()
        self._levels.raise_()
        return self._levels

    def blink_dialog(self):
        from .blink_dialog import BlinkDialog

        dlg = BlinkDialog(self)
        dlg.show()
        return dlg

    def save_picture_dialog(self, path=None):
        """The image as shown on screen (PNG / JPEG), or its data as a 32-bit TIFF."""
        from ..display import save_picture

        if self.viewer.data is None:
            return None
        if path is None:
            stem = self.current_path.stem if self.current_path else "image"
            path, _ = QFileDialog.getSaveFileName(
                self,
                translate("MainWindow", "Save picture"),
                f"{stem}.png",
                "PNG (*.png);;JPEG (*.jpg);;TIFF, 32-bit data (*.tif)",
            )
        if not path:
            return None
        v = self.viewer
        return save_picture(path, v.data, v.interval, v.stretch, v.limits, v.cmap, v.invert)

    def convert_dialog(self, paths=None, folder=None, fmt=None):
        """Batch conversion: FITS files to pictures with the current display interval and stretch."""
        from PySide6.QtWidgets import QInputDialog

        if paths is None:
            paths, _ = QFileDialog.getOpenFileNames(
                self, translate("MainWindow", "Images to convert"), "", images_filter()
            )
            if not paths:
                return None
        from ..io.bayer import fits_paths

        paths = fits_paths(paths)
        if fmt is None:
            choices = {"PNG": "png", "JPEG": "jpg", translate("MainWindow", "TIFF, 32-bit data"): "tif"}
            name, ok = QInputDialog.getItem(
                self,
                translate("MainWindow", "Convert images"),
                translate("MainWindow", "Format:"),
                list(choices),
                0,
                False,
            )
            if not ok:
                return None
            fmt = choices[name]
        if folder is None:
            folder = QFileDialog.getExistingDirectory(self, translate("MainWindow", "Folder for the pictures"))
            if not folder:
                return None
        params = {"fmt": fmt, "interval": self.viewer.interval, "stretch": self.viewer.stretch}
        return self.run_step(
            "image.convert",
            {"images": list(paths), "output_dir": folder},
            params,
            on_done=lambda out: self.statusBar().showMessage(
                translate("MainWindow", "{n} pictures written to {folder}.").format(
                    n=len(out["written"]), folder=folder
                ),
                10000,
            ),
        )

    def plate_solve(self):
        from .. import astrometry

        if astrometry.find_solver() is None:
            QMessageBox.information(
                self,
                translate("MainWindow", "No plate solver"),
                translate(
                    "MainWindow",
                    "Install ASTAP and one of its star databases (hnsky.org/astap.htm), or astrometry.net, "
                    "then try again. Nothing is sent over the internet.",
                ),
            )
            return None
        return self.run_step(
            "astrometry.solve",
            {"image": str(self.current_path)},
            on_done=lambda out: self.open_fits(Path(out["solved"])),
        )

    def split_channels(self):
        """The current colour-camera raw image as three half-size FITS files (R, G, B superpixels, as calibration
        splits them), written next to it and opened."""
        from astropy.io import fits

        from ..io import bayer

        header = self.image_page.header
        pattern = bayer.pattern_of(header) if header is not None else None
        if self.current_path is None or not pattern:
            return []
        data, header, _ = fitsio.read_image(self.current_path)
        paths = []
        for colour, plane in bayer.split(data, pattern).items():
            path = self.current_path.with_name(f"{self.current_path.stem}_{colour}.fits")
            fits.PrimaryHDU(plane, bayer.channel_header(header, pattern, colour)).writeto(path, overwrite=True)
            paths.append(str(path))
        self.open_many(paths)
        return paths

    def stack_open_images(self, drizzle=False, output=None):
        """The images open in the Images window stacked (or drizzled) into one, which then opens (MaxIm DL's
        Combine); the stacking settings are the step's defaults, the Calibration window has them all."""
        images = self.image_page.open_paths()
        if len(images) < 2:
            win = self.area_windows.get("image", self)
            win.statusBar().showMessage(translate("MainWindow", "Open two or more images to stack them."), 8000)
            return None
        if output is None:
            first = Path(images[0])
            suggestion = str(first.with_name(first.stem + ("_drizzle.fits" if drizzle else "_stack.fits")))
            output, _ = QFileDialog.getSaveFileName(
                self, translate("MainWindow", "Save FITS as"), suggestion, FITS_FILTER
            )
            if not output:
                return None

        def done(out):
            if self.engine.project:
                self.engine.project.add_file(Path(out["stack"]), "stack")
            self.open_fits(Path(out["stack"]))

        step_id = "stacking.drizzle" if drizzle else "stacking.stack"
        return self.run_step(step_id, {"images": images, "output": str(output)}, {}, on_done=done, area="image")

    def stack_images(self, images, output, params):
        def done(out):
            if self.engine.project:
                self.engine.project.add_file(Path(out["stack"]), "stack")
            self.calibrate_page.result.setText(
                translate("MainWindow", "Stack written: {path}").format(path=out["stack"])
            )
            self.open_fits(Path(out["stack"]))

        step_id = "stacking.drizzle" if params.pop("drizzle", False) else "stacking.stack"
        return self.run_step(step_id, {"images": images, "output": output}, params, on_done=done, area="calibrate")

    def _show_pixel(self, x, y, value):
        label = translate("MainWindow", "value")
        text = f"x={x:.0f}  y={y:.0f}  {label}={value:.6g}"
        if self.wcs is not None:
            sky = self.wcs.pixel_to_world(x - 1, y - 1)
            text += "  " + sky.to_string("hmsdms", precision=1)
        self.pixel_label.setText(text)
        if getattr(self, "image_pixel_label", None) is not None:  # the cursor read-out of the Images window
            self.image_pixel_label.setText(text)
