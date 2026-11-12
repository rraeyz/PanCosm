"""Guided tasks (plans/interface.md UI-8): a thin bar at the top of a real area window — step n of m, what to do
now, "Show me" marks the control — and the user works in the window itself; there is no separate wizard.

    task = load(path, "tr"); bar = GuidedBar(window, page, task)
"""

import tomllib
from pathlib import Path

from PySide6.QtCore import QRect, Qt, QTimer
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QToolBar

FOLDER = Path(__file__).resolve().parents[2] / "resources" / "guided"


def _text(entry, lang):
    return entry.get(lang) or entry.get("en", "") if isinstance(entry, dict) else str(entry)


def load(path, lang="en"):
    """{"area", "title", "steps": [(widget attribute, text)]} of a script in the language (English as fallback)."""
    doc = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    steps = [(s["widget"], _text(s["text"], lang)) for s in doc["step"]]
    return {"area": doc["area"], "title": _text(doc["title"], lang), "steps": steps}


def available(lang="en"):
    return [load(p, lang) | {"path": str(p)} for p in sorted(FOLDER.glob("*.toml"))]


class GuidedBar(QToolBar):
    def __init__(self, window, page, task):
        super().__init__(task["title"], window)
        self.setObjectName("guided_task")
        self.window_, self.page, self.task, self.index = window, page, task, 0
        self.count, self.text = QLabel(self), QLabel(self)
        self.text.setWordWrap(True)
        self.addWidget(self.count)
        self.addWidget(self.text)
        self.buttons = {}
        parts = (
            ("show", self.tr("Show me"), self.show_me),
            ("back", self.tr("Back"), self.back),
            ("next", self.tr("Next"), self.next),
            ("close", self.tr("Close"), self.close_task),
        )
        for key, label, slot in parts:
            self.buttons[key] = QPushButton(label, self)
            self.buttons[key].clicked.connect(slot)
            self.addWidget(self.buttons[key])
        self.mark = QFrame(window)
        self.mark.setAttribute(Qt.WA_TransparentForMouseEvents)  # the control stays usable under the mark
        self.mark.setStyleSheet("border: 3px solid palette(highlight); border-radius: 6px; background: transparent;")
        self.mark.hide()
        window.addToolBarBreak(Qt.TopToolBarArea)
        window.addToolBar(Qt.TopToolBarArea, self)
        self._show()

    def widget(self):
        found = self.page
        for name in self.task["steps"][self.index][0].split("."):  # "frequency_page.button": a tab's control
            found = getattr(found, name)
        return found

    @staticmethod
    def _bring_forward(w):
        """The tabs and stacks around the control show the page that holds it."""
        from PySide6.QtWidgets import QStackedWidget

        child, parent = w, w.parentWidget()
        while parent is not None:
            if isinstance(parent, QStackedWidget) and parent.indexOf(child) >= 0:
                parent.setCurrentWidget(child)
            child, parent = parent, parent.parentWidget()

    def _show(self):
        n = len(self.task["steps"])
        self.count.setText(self.tr("Step {i} of {n}").format(i=self.index + 1, n=n))
        self.text.setText(self.task["steps"][self.index][1])
        self.buttons["back"].setEnabled(self.index > 0)
        self.buttons["next"].setText(self.tr("Done") if self.index == n - 1 else self.tr("Next"))
        self.mark.hide()

    def show_me(self):
        """Mark the step's control for three seconds (and give it the focus); False when it is not shown now."""
        w = self.widget()
        self._bring_forward(w)
        if not w.isVisible():
            self.window_.statusBar().showMessage(self.tr("That control is folded away: open its section first"), 6000)
            return False
        top_left = w.mapTo(self.window_, w.rect().topLeft())
        self.mark.setGeometry(QRect(top_left, w.size()).adjusted(-4, -4, 4, 4))
        self.mark.show()
        self.mark.raise_()
        w.setFocus()
        QTimer.singleShot(3000, self.mark.hide)
        return True

    def back(self):
        self.index = max(0, self.index - 1)
        self._show()

    def next(self):
        if self.index == len(self.task["steps"]) - 1:
            return self.close_task()
        self.index += 1
        self._show()

    def close_task(self):
        self.mark.deleteLater()
        self.window_.removeToolBar(self)
        self.deleteLater()
