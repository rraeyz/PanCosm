import time
import warnings

import pytest
from fake_devices import FakeCamera, FakeDome, FakeMonitor, FakeMount
from test_observatory import NIGHT, SITE, at

from astrowb.devices.observatory import Observatory
from astrowb.devices.safety import Rules
from astrowb.devices.server import Client, Controller, serve


@pytest.fixture
def api(tmp_path):
    warnings.simplefilter("ignore")
    obs = Observatory(
        SITE, Rules(), now=lambda: NIGHT, mount=FakeMount(), dome=FakeDome(), monitor=FakeMonitor(), camera=FakeCamera()
    )
    ctrl = Controller(obs)
    server = serve(ctrl, "s3cret", port=0)
    url = f"http://127.0.0.1:{server.server_address[1]}"
    yield obs, ctrl, Client(url, "s3cret"), url
    server.shutdown()


def wait(ctrl):
    for _ in range(200):
        if not ctrl.job["running"]:
            return
        time.sleep(0.02)


def test_token_required(api):
    _, _, _, url = api
    with pytest.raises(RuntimeError, match="token"):
        Client(url, "wrong").status()


def test_slew_status_sequence_abort(api, tmp_path):
    obs, ctrl, client, _ = api
    target = at(60, 120)
    client.post("/slew", {"ra": target.ra.deg, "dec": target.dec.deg})
    wait(ctrl)
    st = client.status()
    assert st["safe"] and abs(st["mount"]["alt"] - 60) < 0.1 and not st["mount"]["parked"]
    spec = {
        "out_dir": str(tmp_path),
        "targets": [{"name": "d", "exposures": [{"exptime": 0.01, "count": 2, "kind": "dark"}]}],
    }
    client.post("/sequence", spec)
    wait(ctrl)
    assert len(client.status()["job"]["written"]) == 2
    client.post("/abort")
    with pytest.raises(RuntimeError, match="resume first"):
        client.post("/sequence", spec)
    client.post("/resume")
    client.post("/sequence", spec)
    wait(ctrl)
    assert client.status()["job"]["error"] is None


def test_refused_slew_reports_reason(api):
    obs, ctrl, client, _ = api
    low = at(3, 200)
    client.post("/slew", {"ra": low.ra.deg, "dec": low.dec.deg})
    wait(ctrl)
    assert "below the limit" in client.status()["job"]["error"]
    with pytest.raises(RuntimeError, match="KeyError"):
        client.post("/slew", {"ra": 1})


def test_autofocus_endpoint(api):
    from fake_devices import FakeFocuser, FocusCamera

    obs, ctrl, client, _ = api
    foc = FakeFocuser(5000)
    obs.devices["focuser"], obs.devices["camera"] = foc, FocusCamera(foc, best=5100)
    obs.last_ok["focuser"] = obs.clock()
    client.post("/autofocus", {"exptime": 0.01, "step": 60, "n_steps": 9})
    for _ in range(500):
        if not ctrl.job["running"]:
            break
        time.sleep(0.02)
    assert ctrl.job["error"] is None and abs(foc.Position - 5100) < 10


def test_sky_flats_endpoint(api, tmp_path):
    obs, ctrl, client, _ = api
    client.post("/skyflats", {"count": 2, "out_dir": str(tmp_path), "target_adu": 1000})
    wait(ctrl)
    assert ctrl.job["error"] is None and len(ctrl.job["written"]) == 2


def test_sequence_window_words(api, tmp_path):
    obs, ctrl, client, _ = api
    dusk, dawn = ctrl._when("dusk"), ctrl._when("dawn")
    assert dusk < NIGHT < dawn
    assert ctrl._when("2026-11-15T23:00:00").isot.startswith("2026-11-15T23:00")
    spec = {
        "out_dir": str(tmp_path),
        "targets": [
            {"name": "d", "exposures": [{"exptime": 0.01, "count": 1, "kind": "dark"}], "end": "2026-01-01T00:00"}
        ],
    }
    client.post("/sequence", spec)
    wait(ctrl)
    assert ctrl.job["error"] is None and ctrl.job["written"] == []  # window over: nothing taken


def test_preview_cooler_focuser_filter(api, tmp_path):
    from fake_devices import FakeFilterWheel, FakeFocuser

    obs, ctrl, client, _ = api
    obs.devices["focuser"], obs.devices["filterwheel"] = FakeFocuser(5000), FakeFilterWheel()
    client.post("/cooler", {"temperature": -15, "on": True})
    assert obs.devices["camera"].SetCCDTemperature == -15 and obs.devices["camera"].CoolerOn is True
    client.post("/focuser", {"position": 5123})
    client.post("/filter", {"name": "V"})
    wait(ctrl)
    client.post("/preview", {"exptime": 0.01, "out_dir": str(tmp_path)})
    wait(ctrl)
    assert ctrl.job["error"] is None and "preview" in ctrl.job["written"][0]
    st = client.status()
    assert st["focuser"]["Position"] == 5123 and st["filterwheel"]["Position"] == 2
    assert st["camera"]["CCDTemperature"] == -10.0


def test_download_only_frames_the_observatory_wrote(api, tmp_path):
    from astropy.io import fits

    _, ctrl, client, url = api
    spec = {
        "out_dir": str(tmp_path / "remote"),
        "targets": [{"name": "d", "exposures": [{"exptime": 0.01, "kind": "dark"}]}],
    }
    client.post("/sequence", spec)
    wait(ctrl)
    [frame] = client.status()["job"]["written"]
    local = client.download(frame, tmp_path / "local")
    assert local.parent == tmp_path / "local" and fits.getheader(local)["IMAGETYP"] == "Dark Frame"
    secret = tmp_path / "secret.txt"
    secret.write_text("not for the network")
    for path in (str(secret), str(tmp_path / "remote" / ".." / "secret.txt"), "/etc/passwd"):
        with pytest.raises(RuntimeError, match="not a frame written"):
            client.download(path, tmp_path / "local")
    assert sorted(p.name for p in (tmp_path / "local").iterdir()) == [local.name]  # no partial files left
    with pytest.raises(RuntimeError, match="token"):
        Client(url, "wrong").download(frame, tmp_path / "other")


def test_https_with_a_pinned_certificate(tmp_path):
    from astrowb.devices.tls import ensure_certificate

    cert, key, fp = ensure_certificate(tmp_path)
    assert ensure_certificate(tmp_path)[2] == fp  # made once, then reused
    obs = Observatory(SITE, Rules(), now=lambda: NIGHT, mount=FakeMount(), monitor=FakeMonitor())
    server = serve(Controller(obs), "s3cret", port=0, tls=(cert, key))
    url = f"https://127.0.0.1:{server.server_address[1]}"
    try:
        assert Client(url, "s3cret", fingerprint=fp.upper()).status()["safe"]
        with pytest.raises(RuntimeError, match="does not match"):
            Client(url, "s3cret", fingerprint="00" * 32).status()  # another machine, or someone in between
        with pytest.raises(RuntimeError, match="fingerprint"):
            Client(url, "s3cret").status()
        with pytest.raises(RuntimeError, match="token"):
            Client(url, "wrong", fingerprint=fp).status()
    finally:
        server.shutdown()
