"""The program's own steps that run without a press, each one the user can turn off (the owner, 2026-11-13: "her şey
otomatik olsun gibi bir niyetim yok"): Settings → Automatic steps lists them, and the code asks `on(key)` before it
acts. Every one keeps a button that does the same by hand. Defaults are today's behaviour."""

from PySide6.QtCore import QT_TRANSLATE_NOOP

from ..settings import Settings

STEPS = (  # key, label, what it does; all on by default
    ("calibration.scan_on_folder", QT_TRANSLATE_NOOP("Automatic", "Scan a folder as soon as it is chosen"),
     QT_TRANSLATE_NOOP("Automatic", "Calibration: the frames are sorted by their headers; by hand: Scan")),
    ("photometry.identify_field", QT_TRANSLATE_NOOP("Automatic", "Identify the field when frames are opened"),
     QT_TRANSLATE_NOOP("Automatic", "Photometry: the plate solution and the Gaia and VSX stars of the first frame "
                       "(needs the internet); by hand: Identify the field")),
    ("photometry.suggest_comparisons", QT_TRANSLATE_NOOP("Automatic", "Suggest comparison stars after the target"),
     QT_TRANSLATE_NOOP("Automatic", "Photometry: once the target is clicked; by hand: Suggest comparison stars")),
    ("photometry.choose_radii", QT_TRANSLATE_NOOP("Automatic", "Choose the radii after the comparison stars"),
     QT_TRANSLATE_NOOP("Automatic", "Photometry: from the stars' profiles; by hand: Choose the radii")),
    ("photometry.next_stage", QT_TRANSLATE_NOOP("Automatic", "Open the next stage when a step is done"),
     QT_TRANSLATE_NOOP("Automatic", "Photometry: the rail moves on by itself; by hand: click the stage")),
    ("timeseries.take_light_curve", QT_TRANSLATE_NOOP("Automatic", "Send each measured light curve to Light curves"),
     QT_TRANSLATE_NOOP("Automatic", "It replaces the curve open there; by hand: Period search → in Photometry")),
    ("oc.take_minima", QT_TRANSLATE_NOOP("Automatic", "Add each time of minimum to the O−C list"),
     QT_TRANSLATE_NOOP("Automatic", "Times of minimum and transit mid-times measured in Photometry and Light curves")),
    ("spectroscopy.take_spectra", QT_TRANSLATE_NOOP("Automatic", "Add each reduced spectrum to Velocities"),
     QT_TRANSLATE_NOOP("Automatic", "Long-slit and échelle results; by hand: Add spectra in Velocities")),
)  # fmt: skip


_SETTINGS = []  # the main window's settings (use); else the user's file


def use(settings):
    _SETTINGS[:] = [settings]


def _settings(given):
    return given or (_SETTINGS[0] if _SETTINGS else Settings())


def on(key, settings=None) -> bool:
    return bool(_settings(settings).get(f"auto.{key}", True))


def set_on(key, value, settings=None):
    _settings(settings).set(f"auto.{key}", bool(value))
