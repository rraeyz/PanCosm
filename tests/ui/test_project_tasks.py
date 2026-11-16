"""UI-16.14: the Project window's Tasks tab lists the tasks of every window."""

import threading
from types import SimpleNamespace

from astrowb.ui.kit import tasks
from astrowb.ui.kit.tasks import TaskChip
from astrowb.ui.project_tasks import TasksTab


def _task(i, state):
    done = threading.Event()
    t = SimpleNamespace(id=i, name="x", state=state, progress=0.5, message="", cancelled=False)
    t.cancel = lambda: setattr(t, "cancelled", True)
    t.finished = state in ("done", "failed", "cancelled")
    return t, done


def test_tasks_tab_rows_and_cancel(qtbot):
    tasks.SEEN.clear()
    chip = TaskChip()
    qtbot.addWidget(chip)
    running, _ = _task(1, "running")
    ended, _ = _task(2, "running")
    chip.update_task(running)
    chip.update_task(ended)
    ended.state, ended.finished = "done", True
    chip.update_task(ended)
    chip.update_task(running)  # an update of a known task adds no row
    tab = TasksTab()
    qtbot.addWidget(tab)
    tab.refresh()
    t = tab.table.model.table
    assert len(t) == 2 and list(t["State"]) == ["running", "finished"]
    tab.cancel([0, 1])
    assert running.cancelled
    tasks.SEEN.clear()
