"""A service that answers with JSON of the wrong shape (a list, null) gives a ValueError the windows show, never a
TypeError or AttributeError that no control catches (net sweep, 2026-11-27)."""

import io
import urllib.request

import pytest

from astrowb import updates
from astrowb.services import aavso_vsp, forecast


@pytest.mark.parametrize("body", [b"[]", b"null", b"7"])
def test_update_check_with_a_wrong_shaped_answer(monkeypatch, body):
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: io.BytesIO(body))
    release, error = updates.check()
    assert release is None and error


@pytest.mark.parametrize("answer", [[], None, 7])
def test_vsp_and_forecast_with_a_wrong_shaped_answer(answer):
    for parse in (aavso_vsp.parse, forecast.parse):
        with pytest.raises(ValueError, match="unexpected form"):
            parse(answer)
