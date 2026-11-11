"""The main window's settings, updates, language, look and help commands: a mixin of MainWindow moved out of
main_window.py (plans/architecture.md ARC-4.4); texts keep the main window's translation context."""

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QFileDialog, QMessageBox

from .. import __version__, compute
from ..brand import BRAND
from .kit.widgets import PlotCanvas
from .messages import translate as message_text

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("MainWindow", "…") calls


def privacy_text():
    """What the program sends and runs (ARC-22): in About and in the guide (Getting started → Privacy)."""
    return translate(
        "MainWindow",
        "No usage data is sent anywhere. The program goes online only for what you start (catalogues, archives, "
        "name look-ups, update checks) and, when left on, the weekly Earth-rotation tables. Plugins run with your "
        "rights: a new or changed one waits until you allow it.",
    )


class SettingsActions:
    """Methods of MainWindow (self is the main window)."""

    def set_language(self, code):
        self.settings.set("ui.language", code)
        QMessageBox.information(
            self,
            translate("MainWindow", "Language"),
            translate("MainWindow", "The new language will be used after restarting {app}.").format(
                app=BRAND.display_name
            ),
        )

    def set_theme(self, code):
        from PySide6.QtWidgets import QApplication

        from . import theme

        self.settings.set("ui.theme", code)
        theme.apply(QApplication.instance(), code, theme.font_size(self.settings))
        self._paint_glyphs()  # the symbols take the text colour of the new theme
        for canvas in self.findChildren(PlotCanvas):  # plots already drawn pick up the new colours
            canvas.figure.set_facecolor(theme.colors(code)["window"])
            canvas.draw()

    def _change_font(self, step):
        from PySide6.QtWidgets import QApplication

        from . import theme

        size = theme.change_font(QApplication.instance(), self.settings, step)
        self._paint_glyphs()
        self.statusBar().showMessage(translate("MainWindow", "Text size: {pt:g} pt").format(pt=size), 3000)
        return size

    def show_settings(self):
        """Settings → All settings… (Ctrl+,): every setting in one window with a search field (UI-13)."""
        from .settings_window import SettingsWindow

        window = SettingsWindow(self)
        window.show()
        return window

    def set_compute(self, code):
        self.settings.set("compute.device", code)
        compute.set_mode(code)  # new worker processes inherit it
        self.statusBar().showMessage(compute.describe(), 8000)

    def update_time_tables(self, quiet=False):
        """Download newer Earth-orientation and leap-second tables (plans/architecture.md ARC-1). quiet: the weekly
        update at start-up, which only reports in the status bar and stays silent when offline."""
        from ..core import earth_orientation

        def done(out):
            earth_orientation.use_stored()
            self.statusBar().showMessage(
                translate("MainWindow", "Earth-rotation tables updated: {0}").format(out["status"]), 15000
            )

        def failed(error):
            if quiet:
                self.statusBar().showMessage(
                    translate("MainWindow", "Earth-rotation tables not updated (offline?)"), 8000
                )
            else:
                QMessageBox.warning(
                    self,
                    translate("MainWindow", "Earth-rotation tables"),
                    translate(
                        "MainWindow",
                        "The tables could not be downloaded: {0}\n\nThe tables in use stay; nothing stops working. "
                        "Try again when online.",
                    ).format(str(error).strip().splitlines()[-1]),
                )

        return self.run_step("app.update_time_tables", {}, {}, on_done=done, on_fail=failed)

    def practice_data(self, folder=None):
        """Simulated raw frames of an eclipsing binary night, for the Guide's first-night exercise."""
        folder = folder or QFileDialog.getExistingDirectory(
            self, translate("MainWindow", "Folder for the practice data")
        )
        if not folder:
            return None

        def done(out):
            self.show_workspace("guide")
            self.guide_page.search.setText(translate("MainWindow", "practice"))
            self.statusBar().showMessage(
                translate("MainWindow", "Practice data in {f}: follow 'Your first night' in the Guide.").format(
                    f=folder
                ),
                15000,
            )

        return self.run_step("sample.night", {"folder": folder}, {}, on_done=done)

    def check_updates(self, fetch=None):
        """Ask GitHub for the newest release in the background; the answer comes in a message box."""
        import threading

        from .. import updates

        if not getattr(self, "_updates_connected", False):
            self.updateChecked.connect(self._show_update)
            self._updates_connected = True
        args = {"fetch": fetch} if fetch else {}
        threading.Thread(target=lambda: self.updateChecked.emit(*updates.check(**args)), daemon=True).start()

    def _show_update(self, release, error):
        if error:
            text = translate("MainWindow", "Could not check for updates: {e}").format(e=message_text(error))
        elif release:
            text = translate("MainWindow", "Version {v} is available (you have {c}).").format(
                v=release["version"], c=__version__
            )
            link = translate("MainWindow", "Open the download page")
            text += f"<br><a href='{release['url']}'>{link}</a>"
        else:
            text = translate("MainWindow", "You have the latest version ({c}).").format(c=__version__)
        self.update_box = QMessageBox(QMessageBox.Information, translate("MainWindow", "Updates"), text, parent=self)
        self.update_box.setTextFormat(Qt.RichText)
        self.update_box.setTextInteractionFlags(Qt.TextBrowserInteraction)
        if release and release.get("notes"):  # what changed: the release's notes, under "Show Details…"
            self.update_box.setDetailedText(release["notes"])
        self.update_box.open()

    def about(self):
        QMessageBox.about(
            self,
            translate("MainWindow", "About {app}").format(app=BRAND.display_name),
            f"<b>{BRAND.display_name}</b> {__version__}<br>{BRAND.organization}<br>"
            f"<a href='{BRAND.homepage}'>{BRAND.homepage}</a><br><br>{compute.describe()}<br><br>" + privacy_text(),
        )

    def _set_clock_offset(self, hours):
        """Camera clock - UTC, for every camera raw file and picture opened from now on (all pages)."""
        from ..io import bayer

        bayer.CLOCK_UTC_OFFSET_H = float(hours)
        self.settings.set("camera.clock_utc_offset", float(hours))
