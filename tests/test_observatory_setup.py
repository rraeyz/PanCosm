"""Observatory set-up without hand-editing JSON: Alpaca discovery, the configuration, the dialog."""

import json
import warnings

from test_alpaca import STATE, alpaca_server  # noqa: F401  (fixture)

from astrowb.devices import setup
from astrowb.devices.server import build
from astrowb.settings import Settings


def test_discover_lists_supported_devices(alpaca_server):  # noqa: F811
    found = setup.discover(search=lambda: [alpaca_server, "10.255.255.1:1"], devices_of=_devices_of)
    assert [(d["kind"], d["name"], d["address"]) for d in found] == [
        ("mount", "Sim mount", alpaca_server),
        ("monitor", "Sim cloud sensor", alpaca_server),
    ]  # the switch is not used; the dead server is skipped


def _devices_of(address):
    from alpaca import management

    if address.startswith("10.255"):
        raise ConnectionError("no answer")
    return management.configureddevices(address)


def test_config_problems_and_token_kept(tmp_path):
    site = {"lat": 36.8, "lon": 30.3, "height": 2500}
    cfg = setup.make_config(
        site, [{"kind": "mount", "protocol": "alpaca", "address": "h:1", "number": 0}], phd2="pc:4400"
    )
    assert cfg["phd2"] == {"host": "pc", "port": 4400} and cfg["listen"] == "127.0.0.1:11112"
    assert setup.problems(cfg) == ["no safety monitor or weather sensor: the supervisor cannot see rain or clouds"]
    indi = {"kind": "focuser", "protocol": "indi", "address": "pi:7624", "name": ""}
    assert "focuser: no INDI device name" in setup.problems(setup.make_config(site, [indi]))
    path = tmp_path / "obs.json"
    path.write_text(json.dumps({"token": "keep-me"}))
    setup.save(cfg, path)
    assert json.loads(path.read_text())["token"] == "keep-me"  # remote clients keep working


def test_dialog_finds_saves_and_the_observatory_starts_from_it(qtbot, tmp_path, alpaca_server):  # noqa: F811
    from astrowb.ui.observatory_dialog import ObservatoryDialog

    warnings.simplefilter("ignore")
    settings = Settings(tmp_path)
    dlg = ObservatoryDialog(settings)
    qtbot.addWidget(dlg)
    dlg.find(lambda: setup.discover(search=lambda: [alpaca_server], devices_of=_devices_of))
    qtbot.waitUntil(lambda: dlg.table.rowCount() == 2, timeout=10000)
    dlg.find(lambda: setup.discover(search=lambda: [alpaca_server], devices_of=_devices_of))
    qtbot.waitUntil(lambda: dlg.find_button.isEnabled(), timeout=10000)
    assert dlg.table.rowCount() == 2  # found again: not added twice
    dlg.lat.setValue(36.82)
    dlg.lon.setValue(30.34)
    dlg.min_alt.setValue(20)
    dlg.focus_offsets.setText("L")
    assert dlg.save(tmp_path / "observatory.json") is None and "name=steps" in dlg.status.text()
    dlg.focus_offsets.setText("L=0, B=-30")
    dlg.temp_coeff.setValue(-5)
    path = dlg.save(tmp_path / "observatory.json", start=True)
    cfg = json.loads(open(path).read())
    assert cfg["rules"]["min_alt"] == 20 and set(cfg["devices"]) == {"mount", "monitor"}
    assert settings.get("observatory.config") == path and dlg.start_now
    obs, _ = build(cfg)  # what the observatory process does with the file
    assert STATE["telescope"]["connected"] and obs.rules.min_alt == 20
    again = ObservatoryDialog(settings, path)  # reopened for editing
    qtbot.addWidget(again)
    assert again.table.rowCount() == 2 and again.min_alt.value() == 20
    assert again.focus_offsets.text() == "L=0, B=-30" and again.temp_coeff.value() == -5
    assert obs.focus == {"offsets": {"L": 0, "B": -30}, "temp_coeff": -5.0, "temp_step": 0.5}
