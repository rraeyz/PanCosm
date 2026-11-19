"""Planning's Lowest altitude offers "Save to the profile" (ARC-16)."""

import pytest

from astrowb.core import profiles
from astrowb.settings import Settings
from astrowb.ui.plan_page import PlanPage


@pytest.fixture
def page_for(qtbot, tmp_path_factory):
    def make(**site):
        s = Settings(tmp_path_factory.mktemp("cfg"))
        if site:
            profiles.update(s, "site", **site)
        page = PlanPage(s)
        qtbot.addWidget(page)
        page.show()
        return page

    return make


def test_hidden_when_equal_then_shown_after_change(page_for):
    page = page_for(horizon=30.0)
    assert page.horizon_save.isHidden()
    page.min_alt.setValue(25)
    assert page.horizon_save.isVisible()
    assert "25°" in page.horizon_save.toolTip() and "Default" in page.horizon_save.toolTip()
    page.min_alt.setValue(30)
    assert page.horizon_save.isHidden()


def test_press_saves_and_hides(page_for):
    page = page_for(horizon=30.0)
    page.min_alt.setValue(25)
    page.horizon_save.click()
    assert profiles.section(page.settings, "site")["horizon"] == 25.0
    assert page.horizon_save.isHidden()


def test_profile_without_horizon(page_for):
    page = page_for()
    assert page.horizon_save.isHidden()
    page.min_alt.setValue(22)
    assert page.horizon_save.isVisible()
    page.horizon_save.click()
    assert profiles.section(page.settings, "site")["horizon"] == 22.0
