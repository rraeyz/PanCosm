"""The name a user reads for each setting and input of a step in the Automation window, instead of its key
("clock_utc_offset"); the key stays in the tooltip and in saved files. A name whose meaning depends on the step
is keyed "step id.name"."""

from PySide6.QtCore import QT_TRANSLATE_NOOP, QCoreApplication

NAMES = {
    "arc": QT_TRANSLATE_NOOP("Settings", "Arc frame"),
    "comps_xy": QT_TRANSLATE_NOOP("Settings", "Comparison stars (x y)"),
    "coord": QT_TRANSLATE_NOOP("Settings", "Sky position of the target"),
    "err": QT_TRANSLATE_NOOP("Settings", "Errors"),
    "error": QT_TRANSLATE_NOOP("Settings", "Velocity errors"),
    "error2": QT_TRANSLATE_NOOP("Settings", "Velocity errors, second star"),
    "extra_xy": QT_TRANSLATE_NOOP("Settings", "Check stars and other targets (x y)"),
    "field": QT_TRANSLATE_NOOP("Settings", "Identified field"),
    "flux": QT_TRANSLATE_NOOP("Settings", "Flux"),
    "folder": QT_TRANSLATE_NOOP("Settings", "Folder of the night's frames"),
    "frames": QT_TRANSLATE_NOOP("Settings", "Frames"),
    "guesses": QT_TRANSLATE_NOOP("Settings", "Line identifications"),
    "images": QT_TRANSLATE_NOOP("Settings", "Images"),
    "light_curve": QT_TRANSLATE_NOOP("Settings", "Light curve"),
    "lights": QT_TRANSLATE_NOOP("Settings", "Folder of the lights"),
    "output": QT_TRANSLATE_NOOP("Settings", "Output file"),
    "output_dir": QT_TRANSLATE_NOOP("Settings", "Folder for masters and calibrated frames"),
    "ref_image": QT_TRANSLATE_NOOP("Settings", "Frame the stars were marked on"),
    "rv": QT_TRANSLATE_NOOP("Settings", "Radial velocities"),
    "rv2": QT_TRANSLATE_NOOP("Settings", "Radial velocities, second star"),
    "science": QT_TRANSLATE_NOOP("Settings", "Science frame"),
    "site": QT_TRANSLATE_NOOP("Settings", "Observatory site"),
    "spectra": QT_TRANSLATE_NOOP("Settings", "Spectra"),
    "target_xy": QT_TRANSLATE_NOOP("Settings", "Target position in the first frame (x y)"),
    "template": QT_TRANSLATE_NOOP("Settings", "Template spectrum"),
    "template2": QT_TRANSLATE_NOOP("Settings", "Template of the second star"),
    "time": QT_TRANSLATE_NOOP("Settings", "Times"),
    "apertures": QT_TRANSLATE_NOOP("Settings", "Further aperture radii measured to choose later (px)"),
    "components": QT_TRANSLATE_NOOP("Settings", "Stars in the spectrum (1 or 2)"),
}


def setting_name(step_id, key):
    """The setting's name in the interface language; one without a name (a plugin's, a rare one) is its key with
    spaces."""
    from ..engine import steps

    try:  # a described setting names itself (AUT-1 item 4): the description is the one source
        described = {p.name: p for p in steps.get(step_id).params}
    except KeyError:
        described = {}
    p = described.get(key)
    if p is not None and p.label:
        name = QCoreApplication.translate("Steps", p.label)
        return f"{name} ({p.unit})" if p.unit else name
    text = NAMES.get(f"{step_id}.{key}") or NAMES.get(key)
    return QCoreApplication.translate("Settings", text) if text else str(key).replace("_", " ")
