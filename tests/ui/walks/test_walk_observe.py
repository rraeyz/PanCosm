"""VAL-8: the Observing window as a user goes through it, on simulated devices served over the observatory's own
network protocol: connect with the address and token, slew to a target, take two darks, see the safety change."""

import warnings

import pytest
from fake_devices import FakeCamera, FakeDome, FakeFilterWheel, FakeFocuser, FakeMonitor, FakeMount
from test_observatory import NIGHT, SITE, at

from astrowb.devices.observatory import Observatory
from astrowb.devices.safety import Rules
from astrowb.devices.server import Controller, serve


@pytest.fixture
def observatory():
    warnings.simplefilter("ignore")
    obs = Observatory(SITE, Rules(), now=lambda: NIGHT, mount=FakeMount(), dome=FakeDome(), monitor=FakeMonitor(),
                      camera=FakeCamera(), focuser=FakeFocuser(), filterwheel=FakeFilterWheel())  # fmt: skip
    obs.controller = Controller(obs)
    server = serve(obs.controller, "tok", port=0)
    yield obs, f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


@pytest.mark.parametrize("lang", ["en", "tr"])
def test_connect_slew_take_darks_and_see_the_safety(walk, observatory, tmp_path, lang):
    obs, url = observatory
    h = walk(lang)
    h.area("observe")
    page = h.page
    h.type("url", url)
    h.type("token", "tok")
    h.click("buttons.connect")
    h.wait(lambda: page.status is not None and "safe" in page.status)
    h.type("target", at(60, 120).to_string("hmsdms", sep=":"))
    h.click("buttons.slew")
    h.wait(lambda: not obs.devices["mount"].AtPark and not obs.controller.job["running"], timeout=60)
    h.type("seq_name", "darks")
    kind, _filter, exptime, count = (page.exposures.cellWidget(0, c) for c in range(4))  # the row's own controls
    kind.setCurrentIndex(kind.findData("dark") if kind.findData("dark") >= 0 else kind.findText("dark"))
    exptime.setValue(0.01)
    count.setValue(2)
    h.type("out_dir", str(tmp_path / "frames"))
    h.click("buttons.start")
    h.wait(lambda: len(list((tmp_path / "frames").glob("*.fits"))) == 2, timeout=60)
    safe_text = page.safety.text()  # "Safe" in the window's language
    obs.devices["monitor"].IsSafe = False
    obs.supervise_once()
    page._poll()  # the window asks the observatory every few seconds; the walk does not wait for the timer
    h.wait(lambda: page.safety.text() not in ("", safe_text) and obs.devices["mount"].AtPark, timeout=30)
    h.check()
    assert page.safety.text() not in ("", safe_text)
