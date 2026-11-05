import pytest

from astrowb.planning import ephemerides
from astrowb.planning.targets import TargetError

VSX_AI_DRA = {
    "VSXObject": {
        "Name": "AI Dra",
        "RA2000": "250.68375",
        "Declination2000": "52.69028",
        "VariabilityType": "EA/SD",
        "Period": "1.1988146",
        "Epoch": "2443300.4440",
        "EclipseDuration": "12",
        "MaxMag": "7.05 V",
    }
}
EXO_HATP32 = [
    {
        "pl_name": "HAT-P-32 b",
        "ra": 31.0427614,
        "dec": 46.6878512,
        "pl_orbper": 2.1500082,
        "pl_tranmid": 2455867.402743,
        "pl_trandur": 3.12048,
        "sy_vmag": 11.439,
    }
]


def fake(url, params):
    if "aavso" in url:
        return VSX_AI_DRA if params["ident"] == "AI Dra" else {"VSXObject": []}
    return EXO_HATP32 if "hat-p-32 b" in params["query"].lower() else []


def test_vsx_eclipsing_binary():
    t = ephemerides.vsx("AI Dra", fetch=fake)
    assert t["t0"] == 2443300.444 and t["period"] == 1.1988146 and t["secondary"]
    assert abs(t["duration"] - 0.12 * 1.1988146) < 1e-9 and t["vmag"] == 7.05 and t["ra"] == 250.68375


def test_vsx_pulsator_gives_no_event_epoch():
    data = {"VSXObject": dict(VSX_AI_DRA["VSXObject"], VariabilityType="RRAB")}
    t = ephemerides.vsx("x", fetch=lambda url, params: data)
    assert "t0" not in t and t["period"] == 1.1988146


def test_exoplanet_archive_and_lookup_order():
    t = ephemerides.exoplanet("HAT-P-32", fetch=fake)  # " b" added
    assert t["name"] == "HAT-P-32 b" and abs(t["duration"] - 3.12048 / 24) < 1e-12 and not t["secondary"]
    assert ephemerides.lookup("HAT-P-32 b", fetch=fake)["source"] == "NASA Exoplanet Archive"
    assert ephemerides.lookup("AI Dra", fetch=fake)["source"] == "VSX"
    with pytest.raises(TargetError, match="VSX does not know"):
        ephemerides.lookup("nothing", fetch=fake)


def test_vsx_falls_back_to_vizier_when_aavso_does_not_answer(monkeypatch):
    def blocked(url, params):
        raise OSError("HTTP Error 403: Forbidden")

    monkeypatch.setattr(ephemerides, "_vsx_vizier", lambda name: VSX_AI_DRA if name == "AI Dra" else {})
    star = ephemerides.vsx("AI Dra", fetch=blocked)
    assert star["t0"] == pytest.approx(2443300.444) and star["period"] == pytest.approx(1.1988146)
    with pytest.raises(TargetError, match="VSX does not know"):
        ephemerides.vsx("nobody", fetch=blocked)


def test_cds_mirrors_are_tried_in_turn_and_remembered(tmp_path, monkeypatch):
    from astrowb import mirrors

    monkeypatch.setenv("ASTROWB_CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(mirrors, "_working", {})
    asked = []

    def query(server):
        asked.append(server)
        if "unistra" in server:
            raise ConnectionError("tunnel closed")
        return server

    assert mirrors.cds("simbad", query) == "simbad.harvard.edu"
    monkeypatch.setattr(mirrors, "_working", {})  # a new worker process: read back from the file
    asked.clear()
    assert mirrors.cds("simbad", query) == "simbad.harvard.edu" and asked == ["simbad.harvard.edu"]

    def missing(server):
        raise TargetError("SIMBAD does not know 'x'")

    with pytest.raises(TargetError):  # an answer, not a failure: not retried elsewhere
        mirrors.cds("simbad", missing)
