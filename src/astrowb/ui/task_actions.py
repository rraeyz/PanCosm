"""Running steps from the main window and showing their progress, failures and the Tasks list: a mixin of
MainWindow moved out of main_window.py (plans/architecture.md ARC-4.4); texts keep its translation context."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QDockWidget

from . import advice
from .messages import task_error
from .messages import translate as message_text

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("MainWindow", "…") calls


class TaskActions:
    """Methods of MainWindow (self is the main window)."""

    def run_step(self, step_id, inputs, params=None, on_done=None, on_fail=None, area=None):
        """Run a step as a task; on_done(outputs) is called on the GUI thread when it succeeds, on_fail(message)
        (instead of the error box) when it fails. Never touch widgets from task.add_callback: that runs on a
        background thread. area: the area that asked for it; its window (if it has one) shows the progress."""
        task = self.engine.run_step(step_id, inputs, params)
        if area in self.area_windows:
            self.area_windows[area].track(task)
        if on_done:
            self._on_done[task.id] = on_done
        if on_fail:
            self._on_fail[task.id] = on_fail
        task.add_callback(self.taskUpdated.emit)
        self.taskUpdated.emit(task)
        return task

    def run_step_for(self, area, step_id, inputs, params=None, on_done=None, on_fail=None):
        """run_step for an area: its window shows the progress."""
        return self.run_step(step_id, inputs, params, on_done=on_done, on_fail=on_fail, area=area)

    def _on_task(self, task):
        states = {
            "queued": translate("MainWindow", "queued"),
            "running": translate("MainWindow", "running"),
            "done": translate("MainWindow", "done"),
            "failed": translate("MainWindow", "failed"),
            "cancelled": translate("MainWindow", "cancelled"),
        }
        from .names import step_name

        text = f"{step_name(task.name)} — {states[task.state]} {int(task.progress * 100)}% {message_text(task.message)}"
        if task.id not in self._task_items:
            self.tasks_list.addItem(text)
            self._task_items[task.id] = (task, self.tasks_list.count() - 1)
        self.tasks_list.item(self._task_items[task.id][1]).setText(text)
        self.progress.setVisible(any(not t.finished for t, _ in self._task_items.values()))
        self.progress.setValue(int(task.progress * 100))
        from .kit.window import AreaWindow

        for win in AreaWindow.alive():  # the area window that started it shows it in its status bar
            win.task_update(task)
        if task.finished:
            done = self._on_done.pop(task.id, None)
            fail = self._on_fail.pop(task.id, None)
            if done and task.state == "done":
                done(task.result())
            self._refresh_files()
            if fail and task.state == "failed":
                fail(task_error(task.error))
                return
        if task.state == "failed":
            from .kit.dialogs import ErrorDialog

            ErrorDialog(
                self,
                translate("MainWindow", "Task failed"),
                f"{step_name(task.name)}\n\n{task_error(task.error)}",
                advice.for_trace(task.error).strip(),
                details=str(task.error),  # the full traceback, for reports
                report=self.report_problem,
            ).open()

    def report_problem(self, path=None):
        from .report import report_dialog

        return report_dialog(self, self.settings, self.engine, path)

    def _start_action(self, key):
        actions = {
            "new_project": self.new_project_dialog,
            "open_project": self.open_project_dialog,
            "open_fits": self.open_fits_dialog,
            "profiles": lambda: self.show_settings().show_profiles(),
        }
        actions[key]() if key in actions else self.open_area(key)

    def _dock(self, name, title, widget, area):
        dock = QDockWidget(title, self)
        dock.setObjectName(name)  # stable id for saved layouts; never translated
        dock.setWidget(widget)
        self.addDockWidget(area, dock)
        return dock
