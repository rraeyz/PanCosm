"""Settings in one place (plans/interface.md UI-13): one window (Ctrl+,) with categories and a search field. Every
setting is one row with a line of description; changes apply at once. The window drives the main window's own
settings actions and methods, so the menus and this window always agree.

    SettingsWindow(main).show()        # main: the MainWindow
"""

from PySide6.QtCore import QT_TRANSLATE_NOOP, QCoreApplication
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QListWidget, QStackedWidget, QVBoxLayout, QWidget

from ..core import profiles
from .i18n import LANGUAGES
from .kit.dialogs import Dialog
from .kit.fields import ChoiceField, NumberField, Toggle
from .kit.forms import FormRow

translate = QCoreApplication.translate


# profile fields: (part, field) -> (label, description, kind, unit); kinds: "text" or (min, max, decimals)
PROFILE_FIELDS = {
    ("site", "name"): (
        QT_TRANSLATE_NOOP("SettingsWindow", "Site name"),
        QT_TRANSLATE_NOOP("SettingsWindow", "Shown in the start window's Tonight line"),
        "text",
        "",
    ),
    ("site", "lat"): (
        QT_TRANSLATE_NOOP("SettingsWindow", "Latitude"),
        QT_TRANSLATE_NOOP("SettingsWindow", "North positive"),
        (-90, 90, 4),
        "°",
    ),
    ("site", "lon"): (
        QT_TRANSLATE_NOOP("SettingsWindow", "Longitude"),
        QT_TRANSLATE_NOOP("SettingsWindow", "East positive"),
        (-180, 360, 4),
        "°",
    ),
    ("site", "height"): (
        QT_TRANSLATE_NOOP("SettingsWindow", "Height"),
        QT_TRANSLATE_NOOP("SettingsWindow", "Above sea level"),
        (-500, 9000, 0),
        "m",
    ),
    ("camera", "gain"): (
        QT_TRANSLATE_NOOP("SettingsWindow", "Gain"),
        QT_TRANSLATE_NOOP("SettingsWindow", "Electrons per ADU"),
        (0, 1000, 3),
        "e⁻/ADU",
    ),
    ("camera", "read_noise"): (
        QT_TRANSLATE_NOOP("SettingsWindow", "Read noise"),
        QT_TRANSLATE_NOOP("SettingsWindow", "Noise of one read-out"),
        (0, 1000, 2),
        "e⁻",
    ),
    ("camera", "dark_current"): (
        QT_TRANSLATE_NOOP("SettingsWindow", "Dark current"),
        QT_TRANSLATE_NOOP("SettingsWindow", "Electrons per second per pixel"),
        (0, 1000, 4),
        "e⁻/s",
    ),
    ("camera", "linearity"): (
        QT_TRANSLATE_NOOP("SettingsWindow", "Linear up to"),
        QT_TRANSLATE_NOOP("SettingsWindow", "Where the response stops being linear (0: unknown)"),
        (0, 1e6, 0),
        "ADU",
    ),
    ("camera", "saturation"): (
        QT_TRANSLATE_NOOP("SettingsWindow", "Saturation"),
        QT_TRANSLATE_NOOP("SettingsWindow", "The largest value a pixel holds (0: unknown)"),
        (0, 1e6, 0),
        "ADU",
    ),
    ("observer", "name"): (
        QT_TRANSLATE_NOOP("SettingsWindow", "Observer"),
        QT_TRANSLATE_NOOP("SettingsWindow", "Your name, in reports and FITS headers"),
        "text",
        "",
    ),
    ("observer", "aavso_code"): (
        QT_TRANSLATE_NOOP("SettingsWindow", "AAVSO code"),
        QT_TRANSLATE_NOOP("SettingsWindow", "Your observer code for AAVSO reports"),
        "text",
        "",
    ),
    ("observer", "mpc_code"): (
        QT_TRANSLATE_NOOP("SettingsWindow", "MPC code"),
        QT_TRANSLATE_NOOP("SettingsWindow", "Your observatory code for minor-planet reports"),
        "text",
        "",
    ),
}


def _tr(text):
    """A text marked with QT_TRANSLATE_NOOP where it is written (PROFILE_FIELDS), translated here."""
    return translate("SettingsWindow", text)


# keys of the settings file that are not choices of the user (state, memory of windows, older names)
INTERNAL = ("recent_projects", "recent.", "area.", "dialog.", "split.", "ui.tour_done", "ui.first_run_done",
            "site", "mpc", "observatory", "spectroscopy.profiles", "exposure_calculator", "plan.utc_offset",
            "camera.clock_utc_offset")  # fmt: skip
SHOWN = ("ui.language", "ui.theme", "ui.font_pt", "ui.mode", "ui.toolbar_text", "profile", "compute.device",
         "services.offline", "time.auto_refresh")  # fmt: skip


class SettingsWindow(Dialog):
    def __init__(self, main):
        super().__init__(self.tr("Settings"), main, main.settings, "settings")
        self.main, self.settings = main, main.settings
        self.rows = []  # (category index, FormRow, words searched)
        self.search = QLineEdit(self)
        self.search.setPlaceholderText(self.tr("Find a setting"))
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.filter)
        self.categories = QListWidget(self)
        self.categories.setMaximumWidth(180)
        self.pages = QStackedWidget(self)
        self.categories.currentRowChanged.connect(self.pages.setCurrentIndex)
        body = QHBoxLayout()
        body.addWidget(self.categories)
        body.addWidget(self.pages, 1)
        self.body.addWidget(self.search)
        self.body.addLayout(body, 1)
        self._general()
        self._profiles()
        self._processing()
        self._online()
        self.categories.setCurrentRow(0)
        if self.width() < 400:
            self.resize(760, 560)

    # --- building ---------------------------------------------------------------------------------------------
    def _category(self, title):
        page = QWidget(self)
        lay = QVBoxLayout(page)
        lay.addStretch(1)
        self.pages.addWidget(page)
        self.categories.addItem(title)
        return self.pages.count() - 1

    def _row(self, category, label, control, description, unit=None):
        page = self.pages.widget(category)
        row = FormRow(label, control, unit=unit, help=description, reset=False)
        note = QLabel(description, page)
        note.setProperty("muted", True)
        note.setWordWrap(True)
        lay = page.layout()
        lay.insertWidget(lay.count() - 1, row)
        lay.insertWidget(lay.count() - 1, note)
        self.rows.append((category, row, note, f"{label} {description}".casefold()))
        return control

    def _mirror(self, action):
        """A Toggle that is the menu action's check box (both ways)."""
        toggle = Toggle("", action.isChecked(), self)
        toggle.toggled.connect(lambda _on: action.setChecked(toggle.isChecked()))  # the state now (area_menus._mirror)
        action.toggled.connect(lambda _on: toggle.setChecked(action.isChecked()))
        return toggle

    def _general(self):
        c = self._category(self.tr("General"))
        main = self.main
        lang = ChoiceField(list(LANGUAGES.items()), self.settings.get("ui.language", "en"), self)
        lang.currentIndexChanged.connect(lambda _i: main.set_language(lang.value()))
        self._row(c, self.tr("Language"), lang, self.tr("The language of the program (after a restart)"))
        look = ChoiceField(
            [("dark", self.tr("Dark")), ("light", self.tr("Light"))], self.settings.get("ui.theme", "dark")
        )
        look.currentIndexChanged.connect(lambda _i: main.set_theme(look.value()))
        self._row(c, self.tr("Look"), look, self.tr("Dark or light windows"))
        from . import theme

        size = NumberField(theme.font_size(self.settings), theme.FONT_MIN, theme.FONT_MAX, 1, 0, parent=self)
        size.valueChanged.connect(lambda v: main._change_font(int(v) - theme.font_size(self.settings)))
        self._row(c, self.tr("Text size"), size, self.tr("The size of the text in every window"), "pt")
        names = Toggle("", bool(self.settings.get("ui.toolbar_text", False)), self)
        names.toggled.connect(self._toolbar_text)
        self._row(c, self.tr("Toolbar text"), names, self.tr("The names beside the toolbar's icons"))
        expert = self.tr("Every option open; in Basic mode the rarely changed ones are folded (nothing is removed)")
        self._row(c, self.tr("Expert mode"), self._mirror(main.expert_action), expert)

    def _toolbar_text(self, on):
        from .kit.window import AreaWindow

        self.settings.set("ui.toolbar_text", on)
        for win in AreaWindow.alive():  # the open windows follow at once
            win.toolbar_text_action.setChecked(on)

    def _profiles(self):
        c = self._category(self.tr("Profiles"))
        for (part, field), (label, description, kind, unit) in PROFILE_FIELDS.items():
            value = profiles.section(self.settings, part)[field]
            if kind == "text":
                control = QLineEdit(str(value or ""), self)
                control.editingFinished.connect(
                    lambda p=part, f=field, w=control: profiles.update(self.settings, p, **{f: w.text().strip()})
                )
            else:
                low, high, decimals = kind
                control = NumberField(float(value or 0), low, high, 1, decimals, parent=self)
                control.valueChanged.connect(lambda v, p=part, f=field: profiles.update(self.settings, p, **{f: v}))
            self._row(c, _tr(label), control, _tr(description), unit or None)

    def _processing(self):
        c = self._category(self.tr("Processing"))
        from .. import compute

        device = ChoiceField([("auto", self.tr("Automatic (GPU when useful)")), ("cpu", self.tr("CPU only")),
                              ("gpu", self.tr("GPU"))], compute.mode(), self)  # fmt: skip
        device.currentIndexChanged.connect(lambda _i: self.main.set_compute(device.value()))
        self._row(c, self.tr("Processing device"), device, self.tr("Where the heavy computations run"))

    def _online(self):
        c = self._category(self.tr("Online services"))
        main = self.main
        offline = self.tr("Catalogues, archives and name look-ups answer only from what was fetched before")
        self._row(c, self.tr("Work offline"), self._mirror(main.offline_action), offline)
        tables = self.tr("Kept up to date once a week when online (about 3 MB from the IERS)")
        self._row(c, self.tr("Earth-rotation tables"), self._mirror(main.time_tables_action), tables)

    # --- search -----------------------------------------------------------------------------------------------
    def filter(self, text):
        """Show only the settings whose label or description has every word; categories without one are hidden."""
        words = text.casefold().split()
        hits = set()
        for category, row, note, searched in self.rows:
            match = all(w in searched for w in words)
            row.setVisible(match)
            note.setVisible(match)
            if match:
                hits.add(category)
        for i in range(self.categories.count()):
            self.categories.item(i).setHidden(i not in hits)
        if hits and self.categories.currentRow() not in hits:
            self.categories.setCurrentRow(min(hits))
        return len([r for r in self.rows if all(w in r[3] for w in words)])
