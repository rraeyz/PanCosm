"""The INDI adapters against the real INDI simulator drivers (indilib). Skipped when indiserver is
not installed (CI installs indi-bin for this test)."""

import shutil
import socket
import subprocess
import time
import warnings

import astropy.units as u
import pytest
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.time import Time

from astrowb.devices.server import build

pytestmark = pytest.mark.skipif(shutil.which("indiserver") is None, reason="indiserver not installed")


def _night_site():
    """A site where it is local midnight now: the safety rules refuse daytime slews."""
    from astropy.coordinates import get_sun

    now = Time.now()
    sun_ha_greenwich = (now.sidereal_time("mean", longitude=0).deg - get_sun(now).ra.deg) % 360
    return {"lat": 10.0, "lon": float((180 - sun_ha_greenwich + 180) % 360 - 180), "height": 100}


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def indiserver():
    port = _free_port()
    drivers = ["indi_simulator_telescope", "indi_simulator_ccd", "indi_simulator_wheel", "indi_simulator_focus"]
    proc = subprocess.Popen(
        ["indiserver", "-p", str(port), *drivers], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    deadline = time.monotonic() + 20
    while True:
        try:
            socket.create_connection(("127.0.0.1", port), timeout=1).close()
            break
        except OSError:
            if time.monotonic() > deadline:
                proc.kill()
                pytest.skip("indiserver did not start")
            time.sleep(0.2)
    time.sleep(1.0)  # drivers define their properties
    yield f"127.0.0.1:{port}"
    proc.terminate()
    proc.wait(10)


def test_indi_simulators(indiserver, tmp_path):
    warnings.simplefilter("ignore")
    site = _night_site()
    config = {
        "site": site,
        "devices": {
            "mount": {"indi": indiserver, "device": "Telescope Simulator"},
            "camera": {"indi": indiserver, "device": "CCD Simulator"},
            "filterwheel": {"indi": indiserver, "device": "Filter Simulator"},
            "focuser": {"indi": indiserver, "device": "Focuser Simulator"},
        },
    }
    obs, _ = build(config)
    assert obs.call("filterwheel", "Names")[:3] == ["Red", "Green", "Blue"]

    # a target near the zenith now, so the safety rules accept it
    now = Time.now()
    lst = now.sidereal_time("mean", longitude=site["lon"] * u.deg)
    target = SkyCoord(lst.deg * u.deg, (site["lat"] - 5) * u.deg).transform_to("icrs")
    obs.slew(target, timeout_s=180, poll_s=0.2)
    assert obs.mount_position().separation(target).arcsec < 60

    obs.call("focuser", "Move", 50100)
    deadline = time.monotonic() + 30
    while obs.call("focuser", "IsMoving") and time.monotonic() < deadline:
        time.sleep(0.2)
    assert obs.call("focuser", "Position") == 50100

    from astrowb.devices.sequence import Exposure, Target, run

    paths = run(obs, [Target("zenith", target, [Exposure(0.5, 1, filter="Green")])], tmp_path)
    assert len(paths) == 1
    with fits.open(paths[0]) as hdul:
        assert hdul[0].data.ndim == 2 and hdul[0].data.size > 1000
        assert hdul[0].header["FILTER"] == "Green"
    assert obs.call("filterwheel", "Position") == 1

    obs.park()
    deadline = time.monotonic() + 180
    while not obs.call("mount", "AtPark") and time.monotonic() < deadline:
        time.sleep(0.5)
    assert obs.call("mount", "AtPark")
