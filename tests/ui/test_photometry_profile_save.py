"""Photometry's read noise, dark current and linearity limit offer "Save to the profile" (ARC-16)."""

import pytest

from astrowb.core import profiles
from astrowb.settings import Settings
from astrowb.ui.photometry_page import PhotometryPage


@pytest.fixture
def page_for(qtbot, tmp_path, monkeypatch):
    def make(**camera):
        monkeypatch.setattr("astrowb.settings.config_dir", lambda: tmp_path)
        if camera:
            profiles.update(Settings(), "camera", **camera)
        page = PhotometryPage()
        qtbot.addWidget(page)
        page.show()
        return page

    return make


def test_equal_hidden_changed_shown(page_for):
    page = page_for(read_noise=5.0)
    page.read_noise.setValue(5.0)
    assert page.read_noise_save.isHidden()
    page.read_noise.setValue(7.5)
    assert not page.read_noise_save.isHidden()  # the section may be collapsed
    assert "7.5 e⁻" in page.read_noise_save.toolTip() and "Default" in page.read_noise_save.toolTip()


def test_press_saves_and_hides(page_for):
    page = page_for(read_noise=5.0)
    page.read_noise.setValue(7.5)
    page.read_noise_save.click()
    assert profiles.section(Settings(), "camera")["read_noise"] == 7.5
    assert page.read_noise_save.isHidden()


def test_profile_without_the_value(page_for):
    page = page_for()
    assert page.linearity_save.isHidden()
    page.linearity.setValue(60000)
    assert not page.linearity_save.isHidden()  # the section may be collapsed
    page.linearity_save.click()
    assert profiles.section(Settings(), "camera")["linearity"] == 60000.0
