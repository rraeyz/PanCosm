"""Automation window: Run from here, Stop and the missing-input badges (plans/interface.md UI-16.12)."""

from PySide6.QtCore import QCoreApplication, QObject, Signal

from ..engine import automation, steps
from .automation_schedule import add_schedule_button
from .automation_template import add_template_button

translate = QCoreApplication.translate


def connect_chain(page):
    page.steps.currentRowChanged.connect(page._show_step)
    page.steps.runFromHere.connect(page._run)
    page.steps.stepDropped.connect(lambda sid, at: page.add_step(sid, at))
    page.steps.cardMoved.connect(page._reorder)
    from .step_library import StepLibrary

    add_template_button(page)
    add_schedule_button(page)
    left = page.list.parentWidget().layout()  # the step library, to drag from, goes under the automations
    library = StepLibrary(page)
    left.insertWidget(left.indexOf(page.list) + 1, library, 1)
    after = page.list.nextInFocusChain()  # Tab reads the library right after the automations list, as on screen
    page.list.setTabOrder(page.list, library)
    page.list.setTabOrder(library, after)


def missing_by_step(auto, provided):
    """Per step, the data names a required input needs that nothing gives: not an earlier step's output and not
    among `provided` (the automation's own values and the inputs typed in the form)."""
    have, out = set(provided), []
    for entry in auto["steps"]:
        s = steps.get(entry["step"])
        links = entry.get("inputs", {})
        out.append([k for n in s.inputs for k in automation._keys(links.get(n, n)) if k not in have])
        have.update(s.outputs)
    return out


def show_badges(page):
    provided = set(automation.defaults(page.auto)) | {k for k, v in page.values.items() if v.strip()}
    for row, names in enumerate(missing_by_step(page.auto, provided)):
        text = translate("AutomationRun", "needs {names}").format(names=", ".join(names)) if names else ""
        page.steps.set_badge(row, text)


def run_state(page):
    if getattr(page, "_run_state", None) is None:
        page._run_state = RunState(page)
    return page._run_state


class RunState(QObject):
    """The Run button while a chain runs: "Stop — 40 %", a click stops the chain (the task's own cancel)."""

    changed = Signal(object)  # a task update, which arrives on a worker thread

    def __init__(self, page):
        super().__init__(page)
        self.page, self.task, self.running, self.stopped, self.text = page, None, False, False, ""
        self.changed.connect(self._update)

    def begin(self):
        self.running, self.stopped, self.text = True, False, self.page.run_button.text()
        self._show(0.0)

    def track(self, task):
        self.task = task
        task.add_callback(self.changed.emit)
        if self.stopped:  # Stop came between two steps
            task.cancel()

    def stop(self):
        self.stopped = True
        if self.task is not None:
            self.task.cancel()

    def end(self):
        if self.running:
            self.page.run_button.setText(self.text)
        self.running, self.task = False, None

    def _show(self, progress):
        stop = translate("AutomationRun", "Stop")
        self.page.run_button.setText(f"{stop} — {int(progress * 100)} %")

    def _update(self, task):
        if task is not self.task or not self.running:
            return
        if not task.finished:
            self._show(task.progress)
        elif task.state == "cancelled":  # a cancelled task calls no failure handler: the chain ends here
            self.end()
            self.page.status.setText(translate("AutomationRun", "Stopped."))
