"""UI-16.12: Run from here, Stop and the missing-input badges of the automation chain."""

from astrowb.settings import Settings
from astrowb.ui.automation_page import AutomationPage


class FakeTask:
    def __init__(self):
        self.progress, self.state, self.finished, self.cancelled, self.callbacks = 0.4, "running", False, False, []

    def add_callback(self, fn):
        self.callbacks.append(fn)

    def cancel(self):
        self.cancelled = True


def _page(qtbot, tmp_path):
    page = AutomationPage(Settings(tmp_path))
    qtbot.addWidget(page)
    # two steps: the second one's input "frames" is made by the first
    page.set_automation({"name": "t", "steps": [{"step": "calibration.scan"}, {"step": "calibration.run"}]})
    return page


def test_badges_show_inputs_nothing_gives(qtbot, tmp_path):
    page = _page(qtbot, tmp_path)
    card = lambda i: page.steps._group.button(i)  # noqa: E731
    assert not card(0).badge.isHidden() and "folder" in card(0).badge.text()
    assert "output_dir" in card(1).badge.text() and "frames" not in card(1).badge.text()  # frames: from step 1
    page.edits["folder"].setText("/x")
    page.edits["output_dir"].setText("/y")
    assert card(0).badge.isHidden() and card(1).badge.isHidden()


def test_run_from_here_runs_the_later_steps_and_asks_for_what_earlier_ones_give(qtbot, tmp_path):
    page = _page(qtbot, tmp_path)
    got = []
    page.run_requested.connect(lambda auto, inputs: got.append((auto, inputs)))
    page.edits["output_dir"].setText("/y")
    page._run(1)
    assert not got and "frames" in page.edits and "frames" in page.status.text()
    page.edits["frames"].setText('["a.fits"]')
    page._run(1)
    assert [e["step"] for e in got[0][0]["steps"]] == ["calibration.run"]
    assert len(page.auto["steps"]) == 2  # the automation itself is unchanged


def test_the_card_menu_emits_run_from_here(qtbot, tmp_path):
    page = _page(qtbot, tmp_path)
    with qtbot.waitSignal(page.steps.runFromHere) as sig:
        page.steps._menu(page.steps._group.button(1), page.steps.rect().center())
        from PySide6.QtWidgets import QApplication, QMenu

        menu = next(w for w in QApplication.topLevelWidgets() if isinstance(w, QMenu) and w.isVisible())
        menu.actions()[0].trigger()
    assert sig.args == [1]


def test_run_button_is_stop_while_running(qtbot, tmp_path):
    page = _page(qtbot, tmp_path)
    page.edits["folder"].setText("/x")
    page.edits["output_dir"].setText("/y")
    page._run()
    assert page.run_button.text().startswith("Stop")
    task = FakeTask()
    page.track(task)
    task.callbacks[0](task)
    qtbot.waitUntil(lambda: page.run_button.text() == "Stop — 40 %")
    page._run()  # a second click on the same button stops
    assert task.cancelled
    task.finished, task.state = True, "cancelled"
    task.callbacks[0](task)
    qtbot.waitUntil(lambda: page.run_button.text() == "Run")
    assert page.status.text() == "Stopped."
