"""UI-16.12 / AUT-2.3: the run plan before Run."""

from PySide6.QtWidgets import QDialog, QMainWindow

from astrowb.settings import Settings
from astrowb.ui import automation_plan
from astrowb.ui.automation_page import AutomationPage

AUTO = {"name": "t", "steps": [{"step": "calibration.scan"}, {"step": "calibration.run"}]}


class Host(QMainWindow):
    def __init__(self, settings):
        super().__init__()
        self.settings, self.tabs = settings, []

    def add_result_tab(self, key, title, widget):
        self.tabs.append((key, title, widget))


def _page(qtbot, tmp_path):
    host = Host(Settings(tmp_path))
    qtbot.addWidget(host)
    page = AutomationPage(host.settings, host)
    page.set_automation(AUTO)
    return host, page


def test_plan_text_says_where_inputs_come_from_and_what_is_missing():
    text = automation_plan.plan_text(AUTO, {"folder": "/x"})
    assert "folder ← asked in the form" in text
    assert "frames ← output of step 1" in text
    assert "output_dir ← missing" in text and "needs output_dir" in text
    own = automation_plan.plan_text({**AUTO, "inputs": {"output_dir": {"value": "/o"}}}, {"folder": "/x"})
    assert "output_dir ← the automation's value" in own


def test_run_shows_the_plan_once_as_a_tab_and_remembers_dont_ask(qtbot, tmp_path, monkeypatch):
    host, page = _page(qtbot, tmp_path)
    got = []
    page.run_requested.connect(lambda a, i: got.append(a))
    page.edits["folder"].setText("/x")
    page.edits["output_dir"].setText("/y")
    answers = iter([QDialog.Rejected, QDialog.Accepted])
    monkeypatch.setattr(QDialog, "exec", lambda self: next(answers))
    page._run()
    assert not got and [t[0] for t in host.tabs] == ["run_plan"]  # refused: nothing ran
    monkeypatch.setattr(automation_plan.QCheckBox, "isChecked", lambda self: True)
    page._run_state = None
    page._run()
    assert len(got) == 1 and len(host.tabs) == 1  # the tab is made once
    assert host.settings.get(automation_plan.SKIP_KEY) is True
    page._run_state = None
    monkeypatch.setattr(QDialog, "exec", lambda self: 1 / 0)  # no dialog any more
    page._run()
    assert len(got) == 2 and "output of step 1" in host.tabs[0][2].toPlainText()
