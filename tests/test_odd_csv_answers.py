import pytest

from astrowb.planning.ephemerides import transiting_planets
from astrowb.services import feeds_gaia

ODD = "the service sent an answer in an unexpected form"


@pytest.mark.parametrize("text", ["<html><body>Service unavailable</body></html>", ""])
def test_odd_answers_raise(text, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    with pytest.raises(ValueError, match=ODD):
        feeds_gaia.parse(text)
    with pytest.raises(ValueError, match=ODD):
        transiting_planets(fetch=lambda url: text)


def test_header_only_is_empty_result(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    assert feeds_gaia.parse("#Name, Date, RaDeg, DecDeg, AlertMag, Class, Comment\n") == []
    head = "pl_name,ra,dec,pl_orbper,pl_tranmid,pl_trandur,sy_vmag,pl_trandep\n"
    assert len(transiting_planets(fetch=lambda url: head)["name"]) == 0
