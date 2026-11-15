"""Settings → Data (ARC-20 item 1): the downloaded and cached data with size, place, source and a Remove button."""

from PySide6.QtCore import QT_TRANSLATE_NOOP, QCoreApplication
from PySide6.QtWidgets import QPushButton

from ..core import datapacks

translate = QCoreApplication.translate

# id -> (title, used by)
TEXTS = {
    "pickles": (QT_TRANSLATE_NOOP("DataPacks", "Pickles spectral library"),
                QT_TRANSLATE_NOOP("DataPacks", "Spectroscopy → Classify (template types)")),
    "mk": (QT_TRANSLATE_NOOP("DataPacks", "MK standard spectra"),
           QT_TRANSLATE_NOOP("DataPacks", "Spectroscopy → Classify (MK type)")),
    "phoenix": (QT_TRANSLATE_NOOP("DataPacks", "PHOENIX model spectra and solar atlas"),
                QT_TRANSLATE_NOOP("DataPacks", "Spectroscopy → Atmosphere fit")),
    "earth": (QT_TRANSLATE_NOOP("DataPacks", "Earth-rotation tables"),
              QT_TRANSLATE_NOOP("DataPacks", "Times and positions (the program's own tables are used without them)")),
    "answers": (QT_TRANSLATE_NOOP("DataPacks", "Catalogue and archive answers"),
                QT_TRANSLATE_NOOP("DataPacks", "Look-ups answered again from here without asking")),
}  # fmt: skip


def size_text(n):
    for unit in ("B", "kB", "MB", "GB"):
        if n < 1000 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1000


def build(window, category):
    """Add one row per kind to the settings window's category; each shows its size and removes on a click."""
    base = window.settings.path.parent
    window.data_buttons = {}
    for pack in datapacks.packs(base):
        title, used = TEXTS[pack["id"]]
        button = QPushButton(window)
        button.clicked.connect(lambda _c=False, i=pack["id"]: _remove(window, base, i))
        window.data_buttons[pack["id"]] = button
        where = "\n".join([pack["path"], *pack["source"]])
        button.setToolTip(where)
        note = translate("DataPacks", "{used}. Fetched again when needed.").format(used=translate("DataPacks", used))
        window._row(category, translate("DataPacks", title), button, f"{note} {where.replace(chr(10), ' ← ')}")
        _show(button, pack)


def _show(button, pack):
    button.setText(translate("DataPacks", "{size} — Remove").format(size=size_text(pack["size"])))
    button.setEnabled(pack["files"] > 0)


def _remove(window, base, pack_id):
    from ..core import datapacks as dp

    dp.remove(base, pack_id)
    _show(window.data_buttons[pack_id], next(p for p in dp.packs(base) if p["id"] == pack_id))
