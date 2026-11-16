"""Every window in every language and theme: screenshots at 1366 × 768 and the cut texts found in them
(plans/interface.md UI-15).

    python tools/ui_gallery.py [--langs en,tr,de,es] [--themes dark,light] [--out gallery]

Writes gallery/<area>-<lang>-<theme>.png, a contact sheet gallery/<area>-<lang>.jpg (both themes) and
gallery/measurements.json: per window, the labels and buttons whose
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
    reader says nothing for them (ARC-19). Qt's own buttons (a table's select-all corner, a full toolbar's »)
    are left out."""
    from PySide6.QtWidgets import QAbstractButton

    return [(b.objectName() or type(b).__name__, "no name") for b in window.findChildren(QAbstractButton)
            if b.isVisible() and not b.objectName().startswith("qt_")
            and not (b.text().strip() or b.accessibleName() or b.toolTip())]  # fmt: skip


MIN_TARGET = 22  # px at 96 dpi: the platforms' own tool buttons are 23 (ARC-19)


def small_targets(window, minimum=MIN_TARGET):
    """[(object name or class, "small target")] of visible buttons narrower or lower than minimum: hard to hit
    with a mouse on a touchpad or a shaking hand at night (ARC-19). Qt's own dock and table corner buttons and
    check boxes (their text is part of what a click hits) are left out."""
    from PySide6.QtWidgets import QAbstractButton, QCheckBox, QRadioButton

    return [(b.objectName() or type(b).__name__, "small target") for b in window.findChildren(QAbstractButton)
            if b.isVisible() and not b.objectName().startswith("qt_") and not isinstance(b, QCheckBox | QRadioButton)
            and min(b.width(), b.height()) < minimum]  # fmt: skip


def unreachable(window):
    """[(object name or class, "not reached by Tab")] of visible, enabled controls that take Tab focus but are
    not on the window's focus chain (ARC-19): keyboard users could never get to them."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QWidget

    chain, w = set(), window.nextInFocusChain()
    while w is not window and len(chain) < 20000:
        chain.add(w)
        w = w.nextInFocusChain()
    return [(c.objectName() or type(c).__name__, "not reached by Tab") for c in window.findChildren(QWidget)
            if c.isVisible() and c.isEnabled() and c.focusPolicy() & Qt.TabFocus and c not in chain]  # fmt: skip


def out_of_order(window, tolerance=8):
    """[(object name or class, "Tab goes back up")] of controls the Tab chain reaches up and to the left of the
    control before it: reading order goes down a column, then right to the next column (or down and back to the left
    for a new row); a step up-left is a chain that does not follow the screen (ARC-19). Containers that take focus
    themselves (a scroll area, a tab widget) and a spin box's own line edit are not counted: their contents are."""
    from PySide6.QtCore import QPoint, Qt

    chain, w = [], window.nextInFocusChain()
    while w is not window and w not in chain and len(chain) < 20000:
        chain.append(w)
        w = w.nextInFocusChain()
    tabbable = [c for c in chain if c.isVisible() and c.isEnabled() and c.focusPolicy() & Qt.TabFocus and c.width() > 1
                and not c.objectName().startswith("qt_")]  # fmt: skip
    containers = set()
    for c in tabbable:
        p = c.parentWidget()
        while p is not None:
            containers.add(p)
            p = p.parentWidget()
    found, last = [], None
    for c in tabbable:
        if c in containers:
            continue
        here = c.mapTo(window, QPoint(0, 0))
        if last is not None and here.y() + tolerance < last.y() and here.x() <= last.x() + tolerance:
            found.append((c.objectName() or type(c).__name__, "Tab goes back up"))
        last = here
    return found


def overlapping(window, slack=2):
    """[(object name or class, "overlaps <other>")] of visible labels, buttons and fields that share a layout and
    cover each other by more than slack px both ways (a layout that failed). Parents without a layout are left out:
    a badge over an image is drawn there on purpose."""
    from PySide6.QtWidgets import QAbstractButton, QAbstractSpinBox, QComboBox, QLabel, QLineEdit, QWidget

    kinds = (QAbstractButton, QLabel, QLineEdit, QComboBox, QAbstractSpinBox)
    found = []
    for parent in [window, *window.findChildren(QWidget)]:
        if parent.layout() is None:
            continue
        kids = [c for c in parent.children() if isinstance(c, kinds) and c.isVisible() and c.width() > 1
                and not c.objectName().startswith("qt_")]  # fmt: skip
        for i, a in enumerate(kids):
            for b in kids[i + 1 :]:
                both = a.geometry().intersected(b.geometry())
                if both.width() > slack and both.height() > slack:
                    found.append((a.objectName() or type(a).__name__, f"overlaps {b.objectName() or type(b).__name__}"))
    return found


MAIN_SHARE = 0.55  # UI principle 1: the main view has at least 55 % of the window (width, as tests/ui/test_anatomy.py)


def small_main_view(window):
    """[("main view", "x % of the window")] when the central widget is narrower than MAIN_SHARE of the window."""
    centre = window.centralWidget()
    share = centre.width() / window.width() if centre is not None and window.width() else 1
    return [("main view", f"{share:.0%} of the window")] if share < MAIN_SHARE else []


def _translations(lang):
    """{English source: translation} of every finished translation that differs from its source."""
    import xml.etree.ElementTree as ET

    from astrowb.ui.i18n import I18N_DIR

    path = I18N_DIR / f"app_{lang}.ts"
    if not path.exists():
        return {}
    pairs = {}
    for m in ET.parse(path).iter("message"):
        t = m.find("translation")
        if t is not None and t.text and t.get("type") != "unfinished" and t.text != m.findtext("source"):
            pairs[m.findtext("source")] = t.text
    return pairs


def untranslated(window, lang):
    """[(object name or class, text)] of visible labels and buttons showing an English text while the translation
    file holds a finished, different one for it: a string set around translate() (ARC-18)."""
    from PySide6.QtWidgets import QAbstractButton, QLabel

    pairs = _translations(lang)
    shown = window.findChildren(QLabel) + window.findChildren(QAbstractButton)
    return [(w.objectName() or type(w).__name__, w.text()) for w in shown if w.isVisible() and w.text() in pairs]


def contact_sheet(shots, path):
    """One JPEG of the screenshots (QImage) side by side, each at half size: the dark and the light window of one
    area and language."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage, QPainter

    half = [i.scaledToWidth(i.width() // 2, Qt.SmoothTransformation) for i in shots]
    sheet = QImage(sum(i.width() for i in half), max(i.height() for i in half), QImage.Format_RGB32)
    sheet.fill(0)
    painter, x = QPainter(sheet), 0
    for i in half:
        painter.drawImage(x, 0, i)
        x += i.width()
    painter.end()
    sheet.save(str(path), "JPG", 80)


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
    found, shots = {}, {}
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
                        found[f"{key}-{lang}-{name}"] = (
                            cut_texts(win)
                            + sideways(win)
                            + unnamed(win)
                            + small_targets(win)
                            + unreachable(win)
                            + out_of_order(win)
                            + overlapping(win)
                            + (small_main_view(win) if hasattr(win, "stage_panels") else [])  # stages: UI-16
                            + untranslated(win, lang)
                        )
                        if out:
                            Path(out).mkdir(parents=True, exist_ok=True)
                            shot = win.grab().toImage()
                            shot.save(str(Path(out) / f"{key}-{lang}-{name}.png"))
                            shots.setdefault(f"{key}-{lang}", []).append(shot)
                        win.close()
                finally:
                    main.engine.shutdown()
                    main.close()
        finally:
            for t in translators:
                app.removeTranslator(t)
    for stem, images in shots.items():
        contact_sheet(images, Path(out) / f"{stem}.jpg")
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
