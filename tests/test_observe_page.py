import json
import socket
import time
import warnings

import pytest
from fake_devices import FakeCamera, FakeDome, FakeFilterWheel, FakeFocuser, FakeMonitor, FakeMount
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton
from test_observatory import NIGHT, SITE, at

from astrowb.devices.observatory import Observatory
from astrowb.devices.safety import Rules
from astrowb.devices.server import Client, Controller, serve
from astrowb.settings import Settings


@pytest.fixture
def page(qtbot, tmp_path):
    from astrowb.ui.observe_page import ObservePage

    warnings.simplefilter("ignore")
    obs = Observatory(
        SITE,
        Rules(),
        now=lambda: NIGHT,
        mount=FakeMount(),
        dome=FakeDome(),
        monitor=FakeMonitor(),
        camera=FakeCamera(),
        focuser=FakeFocuser(),
        filterwheel=FakeFilterWheel(),
    )
    obs.controller = Controller(obs)  # for the tests: wait until its job has ended
    server = serve(obs.controller, "tok", port=0)
    p = ObservePage(Settings(tmp_path))
    qtbot.addWidget(p)
    p.url.setText(f"http://127.0.0.1:{server.server_address[1]}")
    p.token.setText("tok")
    yield p, obs
    server.shutdown()


def test_connect_slew_sequence_and_safety_display(page, qtbot, tmp_path):
    p, obs = page
    p.connect_to()
    qtbot.waitUntil(lambda: p.status is not None and "safe" in p.status, timeout=10000)
    assert p.safety.text() == "Safe"
    target = at(60, 120)
    p.target.setText(target.to_string("hmsdms", sep=":"))
    p._slew()
    qtbot.waitUntil(lambda: not obs.devices["mount"].AtPark, timeout=10000)
    # the slew job outlives the unpark on a loaded machine; a sequence started meanwhile is refused ("busy")
    qtbot.waitUntil(lambda: not obs.controller.job["running"], timeout=30000)
    p._show_status(
        p.status
        | {
            "job": {
                "name": "slew",
                "running": False,
                "progress": 0.0,
                "message": "",
                "error": None,
                "written": [],
                "result": None,
            }
        }
    )
    assert p.job.text() == "slew: 100% \nFinished."  # not "0 %" and "0 frames" after a slew
    p.seq_name.setText("darks")
    p.exposures.cellWidget(0, 0).setCurrentText("dark")
    p.exposures.cellWidget(0, 2).setValue(0.01)
    p.exposures.cellWidget(0, 3).setValue(2)
    p.out_dir.setText(str(tmp_path / "frames"))
    finished = []
    p.sequence_finished.connect(finished.append)
    p._start_sequence()
    qtbot.waitUntil(lambda: len(list((tmp_path / "frames").glob("*.fits"))) == 2, timeout=10000)
    p._poll()
    qtbot.waitUntil(lambda: finished == [str(tmp_path / "frames")], timeout=10000)  # automation may take over
    obs.devices["monitor"].IsSafe = False
    obs.supervise_once()
    p._poll()
    qtbot.waitUntil(lambda: p.safety.text().startswith("NOT SAFE"), timeout=10000)
    assert obs.devices["mount"].AtPark
    p.target.setText("nonsense")
    p._slew()
    assert "not understood" in p.job.text()


@pytest.mark.parametrize("tls", [False, True])
def test_observatory_process_starts_and_answers(tmp_path, tls):
    from astrowb.ui.observe_page import launch_observatory

    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    cfg = tmp_path / "obs.json"
    cfg.write_text(json.dumps({"site": {"lat": 36.8, "lon": 30.3}, "listen": f"127.0.0.1:{port}", "tls": tls}))
    url, token, proc = launch_observatory(cfg)
    fp = json.loads(cfg.read_text()).get("tls_fingerprint")
    assert url.startswith("https://" if tls else "http://") and bool(fp) == tls
    try:
        assert json.loads(cfg.read_text())["token"] == token  # a token was generated and saved
        for _ in range(100):
            try:
                st = Client(url, token, timeout=2, fingerprint=fp).status()
                break
            except Exception:
                time.sleep(0.2)
        else:
            pytest.fail("observatory process did not answer")
        assert st["safe"] and st["devices"] == {}
    finally:
        proc.terminate()
        proc.wait(10)


def test_sequence_spec_with_window(page):
    p, _ = page
    p.seq_name.setText("EB")
    p.seq_coord.setText("02:04:10 +46:41:16")
    p.seq_start.setText("dusk")
    p.seq_end.setText("dawn")
    t = p.sequence_spec()["targets"][0]
    assert t["start"] == "dusk" and t["end"] == "dawn" and "ra" in t


def test_preview_cooler_focuser_filter(page, qtbot, tmp_path):
    p, obs = page
    opened = []
    p.preview_ready.connect(opened.append)
    p.connect_to()
    qtbot.waitUntil(lambda: p.filter_name.count() == 4, timeout=10000)  # names come from the wheel
    assert "focuser at 5000" in p.devices.text() and "filter L" in p.devices.text()
    buttons = {b.text(): b for b in p.findChildren(QPushButton)}
    p.cooler_temp.setValue(-20)
    buttons["Cool to"].click()
    assert obs.devices["camera"].SetCCDTemperature == -20 and obs.devices["camera"].CoolerOn
    p.focus_pos.setValue(5150)
    buttons["Move"].click()
    assert obs.devices["focuser"].Position == 5150
    p.filter_name.setCurrentText("V")
    p.out_dir.setText(str(tmp_path / "obs"))
    assert p.take_preview()  # the filter is changed for the preview, the frame comes back to this computer
    qtbot.waitUntil(lambda: bool(opened), timeout=10000)
    assert obs.devices["filterwheel"].Position == 2 and opened[0].startswith(str(tmp_path / "obs" / "preview"))


def test_frames_of_a_remote_observatory_are_copied(page, qtbot, tmp_path, monkeypatch):
    p, obs = page
    p.settings.set("observatory.download_dir", str(tmp_path / "here"))
    monkeypatch.setattr(p, "is_local", lambda paths: False)  # as if the observatory ran on another computer
    finished, previews = [], []
    p.sequence_finished.connect(finished.append)
    p.preview_ready.connect(previews.append)
    p.connect_to()
    p.seq_name.setText("darks")
    p.exposures.cellWidget(0, 0).setCurrentText("dark")
    p.exposures.cellWidget(0, 2).setValue(0.01)
    p.exposures.cellWidget(0, 3).setValue(3)
    p.out_dir.setText(str(tmp_path / "remote" / "night1"))
    p._start_sequence()
    qtbot.waitUntil(lambda: p._poll() or bool(finished), timeout=15000)
    assert finished == [str(tmp_path / "here" / "night1")]
    assert len(list((tmp_path / "here" / "night1").glob("*.fits"))) == 3
    p.take_preview()
    qtbot.waitUntil(lambda: p._poll() or bool(previews), timeout=15000)
    assert previews[0] == str(tmp_path / "here" / "preview" / previews[0].split("/")[-1])


def test_set_up_dialog_starts_the_saved_observatory(page, monkeypatch):
    p, _ = page
    started = []
    monkeypatch.setattr(p, "start_with", started.append)

    class Accepting:
        def __init__(self, settings, path, parent):
            self.path, self.start_now = "/x/observatory.json", True

        def exec(self):
            return 1

    p.set_up(Accepting)
    assert started == ["/x/observatory.json"]


def test_centre_and_polar_results_in_words(page):
    p, _ = page
    assert p.result_text({"errors": [900.0, 12.4]}) == "Centred to 12 arcsec after 2 frames."
    text = p.result_text({"polar": {"total": 31.0, "alt": 12.0, "az": -28.5}})
    assert "31.0′" in text and "lower the axis by 12.0′" in text and "turn it east by 28.5′" in text
    p.target.setText("nonsense")
    assert p.centre() is False and "not understood" in p.job.text()


def test_camera_settings_rotation_and_panel_flats(page, qtbot, tmp_path):
    from fake_devices import FakePanel

    p, obs = page
    p.seq_name.setText("M 42")
    for c, text in ((5, "139"), (6, "21"), (7, "1"), (8, "10, 20, 300, 200")):
        p.exposures.item(0, c).setText(text)
    p.rotation.setText("95")
    t = p.sequence_spec()["targets"][0]
    e = t["exposures"][0]
    assert (e["gain"], e["offset"], e["readout"], e["roi"], t["rotation"]) == (139, 21, 1, [10, 20, 300, 200], 95.0)
    p.load_sequence(t)  # round trip (automations fill the form this way)
    assert p.sequence_spec()["targets"][0] == t
    p.exposures.item(0, 8).setText("10 20")
    with pytest.raises(ValueError, match="sub-frame"):
        p.sequence_spec()
    obs.devices["panel"] = FakePanel()
    obs.last_ok["panel"] = obs.clock()
    p.out_dir.setText(str(tmp_path / "flats"))
    p.exposures.cellWidget(0, 3).setValue(2)
    p.connect_to()
    assert p.panel_flats()
    qtbot.waitUntil(lambda: obs.devices["panel"].log[-1:] == ["off"], timeout=20000)
    assert obs.devices["panel"].log[:2] == ["close", f"on {FakePanel().MaxBrightness}"]


def test_every_sequence_column_shows_its_whole_header(qtbot, tmp_path):
    """German headers were cut at 1366 × 768 ("elichtung (") while the columns stretched (interface I6b (4))."""
    from astrowb.settings import Settings
    from astrowb.ui.observe_page import ObservePage

    page = ObservePage(Settings(tmp_path))
    qtbot.addWidget(page)
    page.resize(700, 600)
    page.show()
    head, model = page.exposures.horizontalHeader(), page.exposures.model()
    for c in range(model.columnCount()):
        text = model.headerData(c, Qt.Horizontal)
        assert head.sectionSize(c) >= head.fontMetrics().horizontalAdvance(text), text
