"""Using the program as a user, by script (plans/validation.md VAL-8).

    h = Harness(qtbot, tmp_path, lang="tr")
    h.area("calibrate"); h.type("folder", path); h.click("scan_button"); h.wait()
    h.click_image(h.page.viewer, x, y); h.check()

Starts the real main window offscreen in a language, finds controls the way the guided tasks name them (the
attribute path on the area's page, "velocity_tab.orbit_button"; else an object or accessible name), brings their
tab or stage forward, clicks,
types and clicks on images the way a mouse does, waits for the tasks, and collects what a user would have met: every
message box shown (closed and recorded), uncaught exceptions, texts left in English in another language, and actions
slower than their budget. Each action leaves a screenshot in `out`; `check()` fails with the list and the last
screenshot's path.
"""

import os
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QCheckBox,
    QFileDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QRadioButton,
    QWidget,
)

I18N = Path(__file__).resolve().parents[2] / "src" / "astrowb" / "resources" / "i18n"
FILE_DIALOGS = {  # what each answers with, from the chosen paths
    "getOpenFileName": lambda p: (p[0] if p else "", ""),
    "getOpenFileNames": lambda p: (p, ""),
    "getSaveFileName": lambda p: (p[0] if p else "", ""),
    "getExistingDirectory": lambda p: p[0] if p else "",
}
# a click's own time, before any task it starts (UI-11: the window answers at once); shortcut: CI's shared runners
# are 2–3 times slower and stall at random, so there the budget only catches a click that hangs
BUDGET_S = 10.0 if os.environ.get("CI") else 2.0


def english_sources(lang):
    """{English source: translation} of the language's .ts, for the texts translated there."""
    if lang == "en":
        return {}
    root = ET.parse(I18N / f"app_{lang}.ts").getroot()
    found = {}
    for m in root.iter("message"):
        src, tr = m.findtext("source") or "", m.find("translation")
        if tr is not None and tr.text and tr.text != src and tr.get("type") != "unfinished":
            found[src] = tr.text
    return found


class Harness:
    def __init__(self, qtbot, folder, lang="en", out=None):
        from astrowb.settings import Settings
        from astrowb.ui import i18n
        from astrowb.ui.main_window import MainWindow

        self.qtbot, self.lang = qtbot, lang
        self.app = QApplication.instance()
        for w in QApplication.topLevelWidgets():  # boxes an earlier test in this process left open are not ours
            if isinstance(w, QMessageBox) and w.isVisible():
                w.close()
        self.translators = i18n.install(self.app, lang) if lang != "en" else []
        settings = Settings(Path(folder) / f"settings-{lang}")
        settings.set("ui.language", lang)
        self.main = MainWindow(settings)
        qtbot.addWidget(self.main)
        self.out = Path(out or Path(folder) / f"walk-{lang}")
        self.out.mkdir(parents=True, exist_ok=True)
        self.problems, self.boxes, self.timings, self.shots = [], [], [], []
        self.window, self.page = self.main, self.main
        self._sources = english_sources(lang)
        self._hook = sys.excepthook
        sys.excepthook = self._exception
        self._answers = []
        self._dialogs = {n: getattr(QFileDialog, n) for n in FILE_DIALOGS}
        for n, shape in FILE_DIALOGS.items():
            setattr(QFileDialog, n, staticmethod(lambda *a, n=n, shape=shape, **k: self._file_dialog(n, shape)))

    def close(self):
        sys.excepthook = self._hook
        for n, fn in self._dialogs.items():
            setattr(QFileDialog, n, fn)
        self.main.engine.shutdown()
        for t in self.translators:
            self.app.removeTranslator(t)

    def answer(self, *paths):
        """The next file dialog is answered with these paths (a user choosing them); none queued is a problem."""
        self._answers.append([str(p) for p in paths])

    def _file_dialog(self, name, shape):
        if not self._answers:
            self.problems.append(f"a file dialog ({name}) the walk did not expect")
            return shape([])
        return shape(self._answers.pop(0))

    def _exception(self, kind, value, tb):
        import traceback

        where = traceback.extract_tb(tb)[-1] if tb else None
        at = f" at {Path(where.filename).name}:{where.lineno} ({where.name})" if where else ""
        self.problems.append(f"exception: {kind.__name__}: {value}{at}")

    # finding and acting
    def area(self, key):
        """Open an area's window, as the start window's button does; later finds look there first."""
        self.main.show_workspace(key)
        self.window = self.main.area_windows.get(key, self.main)
        self.page = getattr(self.main, self.main.PAGES[key])
        self.window.show()
        self.settle()
        return self.window

    def find(self, name):
        from astrowb.ui.kit.guided import GuidedBar

        try:
            found = self.page
            for part in name.split("."):  # "edits.folder": a dict of fields on the page too
                found = found[part] if isinstance(found, dict) else getattr(found, part)
            GuidedBar._bring_forward(found)
            return found
        except (AttributeError, KeyError):
            pass
        for top in [self.window, *QApplication.topLevelWidgets()]:
            w = top.findChild(QWidget, name)
            if w is None:
                w = next((c for c in top.findChildren(QWidget) if c.accessibleName() == name), None)
            if w is not None:
                return w
        raise LookupError(f"no control named {name!r} in {self.window.windowTitle()!r}")

    def _act(self, what, fn, budget):
        start = time.perf_counter()
        fn()
        self.settle()
        took = time.perf_counter() - start
        self.timings.append((what, took))
        if took > budget:
            self.problems.append(f"slow: {what} took {took:.1f} s (budget {budget} s)")
        self.shot(what)

    def click(self, name, budget=BUDGET_S):
        w = self.find(name)
        if not (w.isVisible() and w.isEnabled()):
            self.problems.append(f"cannot click {name}: {'disabled' if w.isVisible() else 'hidden'}")
            return
        # a check box or radio button takes the click on its box and text, not in the empty width beyond them
        pos = QPoint(8, w.height() // 2) if isinstance(w, QCheckBox | QRadioButton) else QPoint()
        self._act(f"click {name}", lambda: QTest.mouseClick(w, Qt.LeftButton, pos=pos), budget)

    def type(self, name, text, budget=BUDGET_S):
        """Type text, or a number written as the field's language writes it (4,6 in Turkish), and press Enter."""
        w = self.find(name)
        if isinstance(text, float):
            text = w.locale().toString(text, "f", w.decimals() if hasattr(w, "decimals") else 6)

        def typing():
            w.setFocus()
            w.clear() if isinstance(w, QLineEdit) else w.lineEdit().selectAll() if hasattr(w, "lineEdit") else None
            QTest.keyClicks(w, text)
            QTest.keyClick(w, Qt.Key_Return)

        self._act(f"type into {name}", typing, budget)

    def choose(self, name, row, budget=BUDGET_S):
        """Click a list's row; a combo box is set and says `activated`, as a choice in its popup does (offscreen clicks
        do not reach the popup)."""
        w = self.find(name)
        if hasattr(w, "visualItemRect"):
            pos = w.visualItemRect(w.item(row)).center()
            self._act(
                f"choose {name} row {row}", lambda: QTest.mouseClick(w.viewport(), Qt.LeftButton, pos=pos), budget
            )
        else:
            self._act(f"choose {name} item {row}", lambda: (w.setCurrentIndex(row), w.activated.emit(row)), budget)

    def cell(self, name, row, column, text, budget=BUDGET_S):
        """Double-click a table's cell, type over it, Enter."""
        w = self.find(name)
        pos = w.visualRect(w.model().index(row, column)).center()

        def typing():
            index = w.model().index(row, column)
            QTest.mouseClick(w.viewport(), Qt.LeftButton, pos=pos)
            QTest.mouseDClick(w.viewport(), Qt.LeftButton, pos=pos)
            if not isinstance(QApplication.focusWidget(), QLineEdit):  # macOS: a double-click may not open it
                w.edit(index)
            editor = QApplication.focusWidget()
            if isinstance(editor, QLineEdit):
                editor.selectAll()
            QTest.keyClicks(editor, text)
            QTest.keyClick(editor, Qt.Key_Return)

        self._act(f"type into {name} cell {row},{column}", typing, budget)
        shown = w.model().data(w.model().index(row, column))  # committed once the events ran
        if shown != text:
            self.problems.append(f"{name} cell {row},{column} shows {shown!r}, typed {text!r}")

    def menu(self, text, budget=BUDGET_S):
        """Trigger the window's menu command with this English source text ("&Open…") or its translation."""
        wanted = {t.replace("&", "") for t in (text, self._sources.get(text, text))}
        for act in self._menu_actions(self.window.menuBar().actions()):
            shown = act.text().replace("&", "")
            if shown in wanted or any(shown.startswith(w + " ") for w in wanted):  # "Undo image operation"
                self._act(f"menu {text}", act.trigger, budget)
                return
        raise LookupError(f"no menu command {text!r} in {self.window.windowTitle()!r}")

    def _menu_actions(self, actions):
        """Every visible command of the menu bar, in its submenus too (the main window's menus are lent to areas)."""
        for act in actions:
            if not act.isVisible():
                continue
            if act.menu() is not None:
                act.menu().aboutToShow.emit()  # menus filled when they open
                yield from self._menu_actions(act.menu().actions())
            else:
                yield act

    def click_image(self, viewer, x, y, budget=BUDGET_S):
        """A click at array pixel (x, y) of an ImageViewer, through its viewport as the mouse gives it."""
        h = viewer.data.shape[0]
        pos = viewer.mapFromScene(QPointF(x + 0.5, h - 0.5 - y))
        self._act(f"click image at {x:.0f},{y:.0f}", lambda: QTest.mouseClick(viewer.viewport(), Qt.LeftButton,
                                                                             pos=pos), budget)  # fmt: skip

    def click_plot(self, plot, ax, x, budget=BUDGET_S):
        """A click on a PlotCanvas at data x, half-way up the axes, through the canvas as the mouse gives it."""
        canvas = plot.canvas
        px = ax.transData.transform((x, 0))[0]
        py = ax.transAxes.transform((0, 0.5))[1]
        ratio = canvas.device_pixel_ratio
        pos = QPoint(round(px / ratio), round((canvas.figure.bbox.height - py) / ratio))
        self._act(f"click plot at {x:g}", lambda: QTest.mouseClick(canvas, Qt.LeftButton, pos=pos), budget)

    def keys(self, text, budget=BUDGET_S):
        """Type into whatever has the focus (an editor a click opened), then Enter."""

        def typing():
            w = QApplication.focusWidget()
            QTest.keyClicks(w, text)
            QTest.keyClick(w, Qt.Key_Return)

        self._act(f"keys {text}", typing, budget)

    # waiting and collecting
    def settle(self):
        for _ in range(3):
            self.app.processEvents()
        self._collect_boxes()

    def busy(self):
        q = self.main.engine.queue
        return bool(q._pending or q._running)

    def wait(self, until=None, timeout=120.0):
        """Until no task runs (and `until()` holds), the results shown; message boxes met on the way recorded."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.qtbot.wait(50)
            self._collect_boxes()
            if not self.busy() and (until is None or until()):
                self.settle()
                return True
        self.problems.append(f"timed out after {timeout:.0f} s waiting in {self.window.windowTitle()!r}")
        return False

    def _collect_boxes(self):
        for w in QApplication.topLevelWidgets():
            if isinstance(w, QMessageBox) and w.isVisible():
                text = " ".join(t for t in (w.windowTitle(), w.text(), w.informativeText()) if t)
                self.boxes.append(text)
                if w.icon() in (QMessageBox.Warning, QMessageBox.Critical):
                    self.problems.append(f"message: {text}")
                w.close()

    def untranslated(self, window=None):
        """Labels, buttons and their tooltips still showing an English source text that the language translates."""
        if not self._sources:
            return []
        found = []
        for w in (window or self.window).findChildren(QWidget):
            if isinstance(w, QLabel | QAbstractButton) and w.isVisible():
                for text in (w.text().replace("&", ""), w.toolTip()):
                    if text in self._sources:
                        found.append(f"{text} ({type(w).__name__} in {type(w.parentWidget()).__name__})")
        return found

    def shot(self, what):
        path = self.out / f"{len(self.shots):02d}-{''.join(c if c.isalnum() else '-' for c in what)[:40]}.png"
        self.window.grab().save(str(path))
        self.shots.append(path)

    def check(self):
        """Fail with everything met: problems, untranslated texts, and the last screenshot to look at."""
        problems = self.problems + [f"untranslated: {t}" for t in self.untranslated()]
        last = self.shots[-1] if self.shots else None
        assert not problems, "\n".join([*problems, f"last screenshot: {last}"])
