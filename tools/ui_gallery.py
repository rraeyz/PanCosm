"""Every window in every language and theme: screenshots at 1366 × 768 and the cut texts found in them
(plans/interface.md UI-15).

    python tools/ui_gallery.py [--langs en,tr,de,es] [--themes dark,light] [--out gallery]

Writes gallery/<area>-<lang>-<theme>.png and gallery/measurements.json: per window, the labels and buttons whose
text does not fit (size hint wider than the widget, without word wrap) and the panels that scroll sideways. The
language "pseudo" is English lengthened by 40 % and accented (ARC-18 item 3). tests/test_gallery.py runs the measuring
part.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
SIZE = (1366, 768)


def cut_texts(window):
    """[(object name or class, text)] of visible labels and buttons whose one-line text is wider than the widget."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QAbstractButton, QLabel, QToolButton

    out = []
    for w in window.findChildren(QLabel) + window.findChildren(QAbstractButton):
        if not w.isVisible() or w.width() <= 1:
            continue
        text = w.text()
        if not text or "<" in text or "\n" in text:  # rich text and several lines are laid out by Qt itself
            continue
        if isinstance(w, QLabel) and w.wordWrap():
            continue
        if isinstance(w, QToolButton) and w.toolButtonStyle() == Qt.ToolButtonIconOnly:
            continue  # the text is the tooltip, not shown
        if type(w).__name__ == "_FoldButton":
            continue  # a section title shortens itself with "…" by design (the whole title in its tooltip)
        needed = w.fontMetrics().horizontalAdvance(text.replace("&", ""))
        icon = w.iconSize().width() + 4 if isinstance(w, QAbstractButton) and not w.icon().isNull() else 0
        room = w.contentsRect().width() - icon - (16 if isinstance(w, QAbstractButton) else 0)  # padding
        if needed > room + 2 and room > 0:
            out.append((w.objectName() or type(w).__name__, text))
    return out


def sideways(window):
    """[(object name or class, "scrolls sideways")] of visible scroll areas whose content is wider than they are."""
    from PySide6.QtWidgets import QScrollArea

    return [(s.objectName() or type(s.widget()).__name__, "scrolls sideways") for s in window.findChildren(QScrollArea)
            if s.isVisible() and s.widget() is not None and s.horizontalScrollBar().isVisible()]  # fmt: skip


def unnamed(window):
    """[(object name or class, "no name")] of visible buttons with no text, accessible name or tooltip: a screen
    reader says nothing for them (ARC-19). Qt's own select-all corner of tables is left out."""
    from PySide6.QtWidgets import QAbstractButton

    return [(b.objectName() or type(b).__name__, "no name") for b in window.findChildren(QAbstractButton)
            if b.isVisible() and b.objectName() != "qt_tableview_cornerbutton"
            and not (b.text().strip() or b.accessibleName() or b.toolTip())]  # fmt: skip


def pseudo_translator():
    """A translator that lengthens every text by 40 % and accents its letters (ARC-18 item 3): the cuts a German or
    Spanish translation would cause show before any translator works. Placeholders and markup stay as they are."""
    import re

    from PySide6.QtCore import QTranslator

    accents = str.maketrans("aeiouAEIOUcnsyz", "àéîõüÀÉÎÕÜçñšÿž")
    keep = re.compile(r"(\{[^}]*\}|<[^>]*>|&\w+;|%\w)")

    class Pseudo(QTranslator):
        def translate(self, context, source, disambiguation=None, n=-1):
            if not source:
                return source
            parts = keep.split(source)
            text = "".join(part if i % 2 else part.translate(accents) for i, part in enumerate(parts))
            return text + "·" * (len(source) * 2 // 5)

        def isEmpty(self):  # Qt asks an empty translator nothing
            return False

    return Pseudo()


def windows(main):
    """(area key, window) for every area that opens a window of its own."""
    from astrowb.ui.start_page import areas

    for key, *_ in areas():
        main.show_workspace(key)
        win = main.area_windows.get(key)
        if win is not None:
            win.resize(*SIZE)
            yield key, win


def run(langs=("en",), themes=("dark",), out=None, settings_dir=None):
    import tempfile

    from PySide6.QtWidgets import QApplication

    from astrowb.settings import Settings
    from astrowb.ui import i18n, theme
    from astrowb.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    found = {}
    for lang in langs:
        if lang == "pseudo":
            translators = [pseudo_translator()]
            app.installTranslator(translators[0])
        else:
            translators = i18n.install(app, lang)
        try:
            for name in themes:
                theme.apply(app, name)
                folder = Path(settings_dir or tempfile.mkdtemp())
                settings = Settings(folder / f"{lang}-{name}")
                settings.set("ui.language", lang)
                main = MainWindow(settings)
                try:
                    for key, win in windows(main):
                        win.show()
                        app.processEvents()
                        found[f"{key}-{lang}-{name}"] = cut_texts(win) + sideways(win) + unnamed(win)
                        if out:
                            Path(out).mkdir(parents=True, exist_ok=True)
                            win.grab().save(str(Path(out) / f"{key}-{lang}-{name}.png"))
                        win.close()
                finally:
                    main.engine.shutdown()
                    main.close()
        finally:
            for t in translators:
                app.removeTranslator(t)
    if out:
        (Path(out) / "measurements.json").write_text(json.dumps(found, indent=1, ensure_ascii=False), "utf-8")
    return found


if __name__ == "__main__":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    args = dict(zip(sys.argv[1::2], sys.argv[2::2], strict=False))
    result = run(args.get("--langs", "en,tr,de,es").split(","), args.get("--themes", "dark,light").split(","),
                 args.get("--out", "gallery"))  # fmt: skip
    cut = {k: v for k, v in result.items() if v}
    print(json.dumps(cut, indent=1, ensure_ascii=False) if cut else "no cut text")
