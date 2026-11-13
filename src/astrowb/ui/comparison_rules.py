"""The comparison-star rules the user sets (plans/photometry.md PHO-17, the rules section): brightness and colour
window, distance, catalogue quality, variables, S/N and how many stars. Kept in the settings; Suggest comparison
stars uses them. Empty settings: the program's defaults (photometry.comprules.ComparisonRules)."""

from PySide6.QtCore import QT_TRANSLATE_NOOP, QCoreApplication
from PySide6.QtWidgets import QCheckBox, QDoubleSpinBox, QFormLayout, QPushButton, QSpinBox

from .kit.dialogs import Dialog

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("ComparisonRules", "…") calls
KEY = "photometry.comparison_rules"


FIELDS = (  # name, label, kind, (min, max, step, decimals)
    (
        "brighter_by_max",
        QT_TRANSLATE_NOOP("ComparisonRules", "At most this much brighter than the target"),
        "mag",
        (0, 8, 0.1, 1),
    ),
    (
        "fainter_by_max",
        QT_TRANSLATE_NOOP("ComparisonRules", "At most this much fainter than the target"),
        "mag",
        (0, 8, 0.1, 1),
    ),
    ("colour_tolerance", QT_TRANSLATE_NOOP("ComparisonRules", "Colour (BP−RP) within"), "mag", (0, 3, 0.05, 2)),
    (
        "colour_required",
        QT_TRANSLATE_NOOP("ComparisonRules", "Leave out stars outside the colour window"),
        "bool",
        None,
    ),
    (
        "max_distance_arcmin",
        QT_TRANSLATE_NOOP("ComparisonRules", "At most this far from the target (0: anywhere)"),
        "arcmin",
        (0, 600, 1, 0),
    ),
    ("catalogue_error_max", QT_TRANSLATE_NOOP("ComparisonRules", "Catalogue error at most"), "mag", (0, 1, 0.005, 3)),
    (
        "exclude_variables",
        QT_TRANSLATE_NOOP("ComparisonRules", "Leave out known variable stars (VSX, Gaia)"),
        "bool",
        None,
    ),
    (
        "exclude_gaia_noisy",
        QT_TRANSLATE_NOOP("ComparisonRules", "Leave out stars Gaia measured as noisy"),
        "bool",
        None,
    ),
    ("min_snr", QT_TRANSLATE_NOOP("ComparisonRules", "Signal-to-noise at least"), "", (1, 10000, 10, 0)),
    ("count", QT_TRANSLATE_NOOP("ComparisonRules", "How many stars"), "int", (1, 50, 1, 0)),
)


def _settings(given=None):
    from .automatic import _settings as main_settings  # the main window's settings, else the user's file

    return main_settings(given)


def rules(settings=None):
    """The rules dict the step takes ({} when the user changed nothing)."""
    stored = _settings(settings).get(KEY)
    return dict(stored) if isinstance(stored, dict) else {}


class RulesDialog(Dialog):
    def __init__(self, settings=None, parent=None):
        from ..photometry.comprules import ComparisonRules

        settings = _settings(settings)
        super().__init__(translate("ComparisonRules", "Comparison-star rules"), parent, settings, "comparison_rules")
        self.settings, defaults = settings, ComparisonRules()
        now = vars(defaults) | rules(settings)
        form = QFormLayout()
        self.widgets = {}
        for name, label, kind, rng in FIELDS:
            if kind == "bool":
                w = QCheckBox(self)
                w.setChecked(bool(now[name]))
            else:
                lo, hi, step, dec = rng
                w = QSpinBox(self) if kind == "int" else QDoubleSpinBox(self)
                w.setRange(lo, hi)
                w.setSingleStep(step)
                if kind != "int":
                    w.setDecimals(dec)
                    w.setSuffix(f" {kind}" if kind else "")
                w.setValue(now[name] or 0)
            self.widgets[name] = w
            form.addRow(translate("ComparisonRules", label), w)
        self.body.addLayout(form)
        reset = QPushButton(translate("ComparisonRules", "The program's defaults"), self)
        reset.clicked.connect(lambda: self._fill(vars(defaults)))
        self.button_row.addWidget(reset)
        self.add_buttons(translate("ComparisonRules", "Use these rules"))

    def _fill(self, values):
        for name, w in self.widgets.items():
            (w.setChecked if isinstance(w, QCheckBox) else w.setValue)(values[name] or 0)

    def values(self):
        out = {n: (w.isChecked() if isinstance(w, QCheckBox) else w.value()) for n, w in self.widgets.items()}
        out["max_distance_arcmin"] = out["max_distance_arcmin"] or None
        out["count"] = int(out["count"])
        return out

    def accept(self):
        self.settings.set(KEY, self.values())
        super().accept()
