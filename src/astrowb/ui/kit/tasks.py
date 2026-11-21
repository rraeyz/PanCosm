"""The window's tasks (plans/interface.md UI-9): a chip in the toolbar with the number running; its popover lists
each task with its state, progress, elapsed and estimated time, and Cancel.

    chip = TaskChip(window); chip.update_task(task)      # an engine task (id, name, state, progress, message)
"""

import time

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QMenu, QToolButton

from .icons import icon

SEEN = []  # every task of this run, all windows: {area, task, wall, mono, ended} (Project → Tasks)
SEEN_MAX = 200  # the oldest go first
KEEP = 10  # finished tasks listed after the running ones
ESTIMATE_FROM = 0.05  # no estimate before 5 % (a guess would be wrong)


def eta(elapsed, progress):
    """Seconds left from the task's own progress reports, or None before ESTIMATE_FROM."""
    if progress < ESTIMATE_FROM or progress >= 1:
        return None
    return elapsed * (1 - progress) / progress


def _clock(seconds):
    seconds = int(round(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}" if seconds >= 60 else f"{seconds} s"


class TaskChip(QToolButton):
    def __init__(self, parent=None, name_of=str, report=None):
        super().__init__(parent)
        self.name_of = name_of  # step id -> words (ui/names.step_name)
        self.report = report  # Help → Report a problem…, offered under a failed task
        self.tasks, self.started = {}, {}  # id -> task, id -> monotonic start
        self.setIcon(icon("tasks", self, 16))
        self.setAutoRaise(True)
        self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.setPopupMode(QToolButton.InstantPopup)
        self.setMenu(QMenu(self))
        self.menu().aboutToShow.connect(self._fill)
        self._show()

    def running(self):
        return [t for t in self.tasks.values() if not t.finished]

    def update_task(self, task):
        self.tasks[task.id] = task
        self.started.setdefault(task.id, time.monotonic())
        entry = next((e for e in SEEN if e["task"] is task), None)
        if entry is None:
            entry = {"area": self.window().windowTitle(), "task": task, "wall": time.time(), "mono": time.monotonic(),
                     "ended": None}  # fmt: skip
            SEEN.append(entry)
            del SEEN[:-SEEN_MAX]
        if task.finished and entry["ended"] is None:
            entry["ended"] = time.monotonic()
        done = [i for i, t in self.tasks.items() if t.finished]
        for i in done[:-KEEP] if len(done) > KEEP else ():
            self.tasks.pop(i)
            self.started.pop(i, None)
        self._show()

    def row_text(self, task, now=None):
        now = time.monotonic() if now is None else now
        elapsed = now - self.started.get(task.id, now)
        name = self.name_of(task.name)
        states = {"queued": self.tr("waiting"), "done": self.tr("finished"), "failed": self.tr("failed"),
                  "cancelled": self.tr("cancelled")}  # fmt: skip
        if task.state in states:
            return f"{name} — {states[task.state]}"
        left = eta(elapsed, task.progress)
        from ..messages import translate

        phase = f" · {translate(task.message)}" if getattr(task, "message", "") else ""  # "reading", "measuring"…
        text = f"{name} — {int(task.progress * 100)} %{phase} · {_clock(elapsed)}"
        return text + (self.tr(" · about {left} left").format(left=_clock(left)) if left is not None else "")

    def _show(self):
        n = len(self.running())
        self.setText(str(n) if n else "")
        self.setToolTip(self.tr("{n} tasks running").format(n=n) if n else self.tr("No task running"))
        self.setEnabled(bool(self.tasks))

    def _fill(self):
        from ..messages import translate

        menu = self.menu()
        menu.clear()
        tasks = sorted(self.tasks.values(), key=lambda t: (t.finished, -self.started.get(t.id, 0)))
        for task in tasks:
            if task.state == "failed" and self.report is not None:
                menu.addMenu(self.row_text(task)).addAction(self.tr("Report a problem…"), lambda: self.report())
            elif task.finished and getattr(task, "timeline", None):  # how long each phase took (ARC-17)
                sub = menu.addMenu(self.row_text(task))
                for phase, took in task.timeline:
                    sub.addAction(f"{translate(phase)}: {took:.1f} s").setEnabled(False)
            elif task.finished:
                menu.addAction(self.row_text(task)).setEnabled(False)
            else:
                sub = menu.addMenu(self.row_text(task))
                sub.addAction(self.tr("Cancel"), task.cancel)
        if not tasks:
            menu.addAction(self.tr("No task running")).setEnabled(False)


class HeldButton(QObject):
    """A stage's main button while the work it started runs (UI-9): it shows "Stop — 40 %" and a click (or Space /
    Enter) stops the work instead of starting it again; back as it was when the work ends. Esc stops it too."""

    def __init__(self, button, cancel=lambda: None):
        super().__init__(button)
        self.button, self.text, self.cancel = button, button.text(), cancel
        button.installEventFilter(self)

    def eventFilter(self, obj, event):
        kind = event.type()
        keys = (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter)
        if kind in (QEvent.MouseButtonPress, QEvent.MouseButtonDblClick, QEvent.MouseButtonRelease):
            if kind == QEvent.MouseButtonRelease:
                self.cancel()
            return True  # the click never reaches the button, so its own action is not started twice
        if kind in (QEvent.KeyPress, QEvent.KeyRelease) and event.key() in keys:
            if kind == QEvent.KeyRelease and not event.isAutoRepeat():
                self.cancel()
            return True
        return False

    def show(self, task):
        if task.finished:
            self.button.removeEventFilter(self)
            self.button.setText(self.text)
        else:
            stop = self.tr("Stop")
            self.button.setText(f"{stop} — {int(task.progress * 100)} %")


def hold(widget, cancel=lambda: None):
    """The HeldButton for the widget that started a task when it is a stage's main (primary) button, else None
    (a click gives a push button the focus, so the focus names the button)."""
    from PySide6.QtWidgets import QPushButton

    return HeldButton(widget, cancel) if isinstance(widget, QPushButton) and widget.property("primary") else None
