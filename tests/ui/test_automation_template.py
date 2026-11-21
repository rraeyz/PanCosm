"""UI-16.12: Save as template."""

from astrowb.settings import Settings
from astrowb.ui.automation_page import AutomationPage
from astrowb.ui.automation_template import save_template


def test_save_as_template_lists_it_and_refuses_a_used_name(qtbot, tmp_path):
    page = AutomationPage(Settings(tmp_path))
    qtbot.addWidget(page)
    page.set_automation({"name": "t", "steps": [{"step": "fits.save_as"}]})
    path = save_template(page, "My chain")
    assert path.exists() and page.list.currentItem().text().startswith("My chain")
    assert "(template)" in page.list.currentItem().text() or "şablon" in page.list.currentItem().text().lower()
    assert save_template(page, "my chain") is None
    assert "exists" in page.status.text()
    assert page.template_button.text()
