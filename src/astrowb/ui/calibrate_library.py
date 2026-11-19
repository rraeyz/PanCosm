"""Calibrate stage and the library of masters (CAL-7): what the plan says of a library master, and the run's masters
filed after it."""

from PySide6.QtCore import QCoreApplication

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("CalibrateLibrary", "…") calls


def library_text(page, kind, n):
    """A library master found for a light: used (within its validity) or only noted (older than it)."""
    kind = page._kind_names()[kind]
    if n["used"]:
        return translate("CalibrateLibrary", "{kind} from the library, {age:.0f} days old").format(
            kind=kind, age=n["age"]
        )
    return translate(
        "CalibrateLibrary", "library {kind} {age:.0f} days old ({kind} valid {days:g} d); calibrated without it"
    ).format(kind=kind, age=n["age"], days=n["valid_days"])


def library_line(page, out):
    """The run's masters filed in the library (Settings → Files, on by default), and those it took from it."""
    from ..calibration.library_use import add_masters, library_folder
    from ..settings import Settings

    settings, parts = Settings(), []
    if out.get("library_used"):
        parts.append(
            translate("CalibrateLibrary", "{n} masters taken from the library.").format(n=len(out["library_used"]))
        )
    if settings.get("calibration.add_to_library", True):
        try:
            n = add_masters(library_folder(settings), out["masters"])
        except (OSError, ValueError) as e:  # the library is a convenience: said, the run stays done
            return str(e)
        if n:
            parts.append(translate("CalibrateLibrary", "{n} masters added to the library.").format(n=n))
    return " ".join(parts)
