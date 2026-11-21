"""UI-16.12: "on error" of the selected step in the inspector."""

from astrowb.settings import Settings
from astrowb.ui.automation_page import AutomationPage


def test_on_error_choice_is_kept_in_the_step(qtbot, tmp_path):
    page = AutomationPage(Settings(tmp_path))
    qtbot.addWidget(page)
    page.set_automation(
        {"name": "t", "steps": [{"step": "calibration.scan"}, {"step": "calibration.run", "on_error": "skip"}]}
    )
    box = page.error_box
    assert box.buttons["stop"].isChecked() and "on_error" not in page.auto["steps"][0]
    box.buttons["continue"].setChecked(True)
    assert page.auto["steps"][0]["on_error"] == "continue"
    page.steps.setCurrentRow(1)
    assert box.buttons["skip"].isChecked() and page.auto["steps"][1]["on_error"] == "skip"  # showing does not write
    box.buttons["stop"].setChecked(True)
    assert "on_error" not in page.auto["steps"][1] and page.auto["steps"][0]["on_error"] == "continue"
