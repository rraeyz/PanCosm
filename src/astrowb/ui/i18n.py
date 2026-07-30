"""Load Qt translations (.qm compiled from resources/i18n/*.ts)."""

from importlib.resources import files
from pathlib import Path

from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator

I18N_DIR = Path(str(files("astrowb") / "resources" / "i18n"))
LANGUAGES = {"en": "English", "tr": "Türkçe", "de": "Deutsch", "es": "Español"}  # native names, never translated


def system_language() -> str:
    lang = QLocale.system().name().split("_")[0]
    return lang if lang in LANGUAGES else "en"


def install(app, language: str) -> list[QTranslator]:
    """Install app and Qt base translations for language. Keep the returned list alive."""
    loaded = []
    if language == "en":
        return loaded
    for name, folder in (("app", I18N_DIR), ("qtbase", QLibraryInfo.path(QLibraryInfo.TranslationsPath))):
        tr = QTranslator(app)
        if tr.load(f"{name}_{language}", str(folder)):
            app.installTranslator(tr)
            loaded.append(tr)
    return loaded
