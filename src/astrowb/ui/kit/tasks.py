"""The window's tasks (plans/interface.md UI-9): a chip in the toolbar with the number running; its popover lists
each task with its state, progress, elapsed and estimated time, and Cancel.

    chip = TaskChip(window); chip.update_task(task)      # an engine task (id, name, state, progress, message)
"""

import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMenu, QToolButton

from .icons import icon

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


class HeldButton:
    """A stage's main button while the work it started runs (UI-9): disabled, so the work is not started twice,
    and showing the progress; back as it was when the work ends. Esc or Cancel stop the work."""

    def __init__(self, button):
        self.button, self.text = button, button.text()
        button.setEnabled(False)

    def show(self, task):
        if task.finished:
            self.button.setText(self.text)
            self.button.setEnabled(True)
        else:
            self.button.setText(f"{self.text} — {int(task.progress * 100)} %")


def hold(widget):
    """The HeldButton for the widget that started a task when it is a stage's main (primary) button, else None
    (a click gives a push button the focus, so the focus names the button)."""
    from PySide6.QtWidgets import QPushButton

    return HeldButton(widget) if isinstance(widget, QPushButton) and widget.property("primary") else None
