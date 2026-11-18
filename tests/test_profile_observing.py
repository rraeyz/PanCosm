"""The observatory set-up starts its lowest altitude from the profile site's horizon (ARC-16)."""

import json

import pytest

from astrowb.core import profiles
from astrowb.devices import setup
from astrowb.settings import Settings
from astrowb.ui.observatory_dialog import ObservatoryDialog


@pytest.fixture
def dialog_for(qtbot, tmp_path_factory):
    def make(**site):
        s = Settings(tmp_path_factory.mktemp("cfg"))
        profiles.update(s, "site", **site)
        dlg = ObservatoryDialog(s)
        qtbot.addWidget(dlg)
        return dlg

    return make


def test_horizon_is_the_default_lowest_altitude(dialog_for):
    assert dialog_for().min_alt.value() == setup.RULE_DEFAULTS["min_alt"]
    assert dialog_for(horizon=0).min_alt.value() == setup.RULE_DEFAULTS["min_alt"]
    assert dialog_for(horizon=25.0).min_alt.value() == 25.0


def test_a_configured_value_overrides_the_profile(dialog_for, tmp_path):
    path = tmp_path / "obs.json"
    path.write_text(json.dumps({"rules": {"min_alt": 40}}))
    dlg = dialog_for(horizon=25.0)
    dlg.load(path)
    assert dlg.min_alt.value() == 40
