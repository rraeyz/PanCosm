import time
import warnings
import xml.etree.ElementTree as ET

import numpy as np
import pytest
from fake_indi import CCD, TEL, WX, FakeIndiServer
from test_observatory import NIGHT, at

from astrowb.devices.server import build


@pytest.fixture
def indi():
    return FakeIndiServer()


def test_observatory_over_indi(indi, tmp_path):
    warnings.simplefilter("ignore")
    addr = f"127.0.0.1:{indi.port}"
    config = {
        "site": {"lat": 36.82, "lon": 30.34, "height": 2500},
        "devices": {
            "mount": {"indi": addr, "device": TEL},
            "camera": {"indi": addr, "device": CCD},
            "monitor": {"indi": addr, "device": WX},
        },
    }
    obs, _ = build(config)
    obs.now = lambda: NIGHT
    target = at(60, 120)
    obs.slew(target, poll_s=0.05)
    assert not indi.state["parked"]
    assert obs.mount_position().separation(target).arcsec < 1  # waited for the Busy -> Ok cycle
    from astrowb.devices.sequence import Exposure, Target, run

    paths = run(obs, [Target("t", None, [Exposure(0.01, 2, kind="dark")])], tmp_path)
    from astropy.io import fits

    assert len(paths) == 2 and fits.getdata(paths[0]).shape == (30, 40)
    assert np.all(fits.getdata(paths[0]) == 1000)
    assert obs.supervise_once() == []
    # the weather station raises an alert: the supervisor parks over INDI
    client = obs.devices["monitor"].client
    client._handle(
        ET.fromstring(
            f'<setLightVector device="{WX}" name="WEATHER_STATUS" state="Alert"><oneLight name="WEATHER_RAIN_HOUR">Alert'
            "</oneLight></setLightVector>"
        )
    )
    assert obs.supervise_once() == ["safety monitor reports unsafe"]
    for _ in range(50):
        if indi.state["parked"]:
            break
        time.sleep(0.02)
    assert indi.state["parked"]
