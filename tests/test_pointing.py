"""Plate-solve pointing: centring with a mount that points off, and polar alignment with a known error."""

import time
import warnings

import astropy.units as u
import numpy as np
import pytest
from astropy.coordinates import SkyCoord
from fake_devices import FakeCamera, FakeDome, FakeMonitor, FakeMount
from test_observatory import NIGHT, SITE, at

from astrowb.devices import pointing
from astrowb.devices.observatory import Observatory
from astrowb.devices.safety import Rules
from astrowb.devices.server import Client, Controller, serve


class OffsetMount(FakeMount):
    """Points 0.4 deg off in RA and 0.25 deg in Dec until it is synced (J2000 coordinates)."""

    def __init__(self):
        super().__init__()
        self.EquatorialSystem = 2
        self.err, self.corr = np.array([0.4 / 15, 0.25]), np.zeros(2)  # hours, degrees
        self.syncs = 0

    def physical(self):
        ra, dec = np.array([self.RightAscension, self.Declination]) + self.err - self.corr
        return SkyCoord(ra * u.hourangle, dec * u.deg)

    def SyncToCoordinates(self, ra, dec):
        p = self.physical()
        self.corr = self.corr + np.array([p.ra.hour - self.RightAscension, p.dec.deg - self.Declination])
        self.RightAscension, self.Declination = ra, dec
        self.syncs += 1


def observatory(mount):
    warnings.simplefilter("ignore")
    return Observatory(
        SITE, Rules(), now=lambda: NIGHT, mount=mount, dome=FakeDome(), monitor=FakeMonitor(), camera=FakeCamera()
    )


def test_center_syncs_until_the_target_is_in_the_middle():
    mount = OffsetMount()
    obs = observatory(mount)
    target = at(60, 120)
    errors = pointing.center(obs, target, mount.physical, tolerance_arcsec=5)
    assert errors[0] > 1000 and errors[-1] < 5 and mount.syncs == 1  # one sync fixes a constant offset


def tan_header(centre, shape):
    ny, nx = shape
    return {
        "CTYPE1": "RA---TAN",
        "CTYPE2": "DEC--TAN",
        "CRVAL1": centre.ra.deg,
        "CRVAL2": centre.dec.deg,
        "CRPIX1": (nx - 1) / 2 + 1,
        "CRPIX2": (ny - 1) / 2 + 1,
        "CD1_1": -0.0005,
        "CD1_2": 0.0,
        "CD2_1": 0.0,
        "CD2_2": 0.0005,
    }


def test_center_through_the_observatory_api(tmp_path):
    from astropy.io import fits

    mount = OffsetMount()
    obs = observatory(mount)
    ctrl = Controller(obs)
    ctrl.solve = lambda path, ra, dec: fits.Header(tan_header(mount.physical(), fits.getdata(path).shape))
    server = serve(ctrl, "t", port=0)
    try:
        client = Client(f"http://127.0.0.1:{server.server_address[1]}", "t")
        target = at(60, 120)
        client.post("/center", {"ra": target.ra.deg, "dec": target.dec.deg, "exptime": 0.01, "out_dir": str(tmp_path)})
        for _ in range(300):
            if not ctrl.job["running"]:
                break
            time.sleep(0.02)
        job = client.status()["job"]
        assert job["error"] is None and job["result"]["errors"][-1] < 30
    finally:
        server.shutdown()


def rotate(v, axis, angle_deg):
    """Rodrigues rotation of v about a unit axis."""
    a = np.radians(angle_deg)
    return v * np.cos(a) + np.cross(axis, v) * np.sin(a) + axis * np.dot(axis, v) * (1 - np.cos(a))


def three_points(axis_ha, axis_dec, start=(20.0, 70.0), step=30.0):
    axis = pointing._unit(axis_ha, axis_dec)
    v0 = pointing._unit(*start)
    out = []
    for k in range(3):
        x, y, z = rotate(v0, axis, k * step)
        out.append((float(np.degrees(np.arctan2(-y, x))), float(np.degrees(np.arcsin(z)))))
    return out


@pytest.mark.parametrize("lat", [37.0, 52.0])
def test_polar_error_signs_and_size(lat):
    # axis tilted 30' from the pole towards the meridian (towards the zenith): too high by 30'
    total, alt, az = pointing.polar_error(three_points(0.0, 89.5), lat)
    assert total == pytest.approx(30, abs=0.01) and alt == pytest.approx(30, abs=0.3) and abs(az) < 0.3
    # tilted towards the east (hour angle -90): azimuth error +30', altitude unchanged
    total, alt, az = pointing.polar_error(three_points(-90.0, 89.5), lat)
    assert az == pytest.approx(30, abs=0.3) and abs(alt) < 0.3
    assert pointing.polar_error(three_points(123.0, 90.0), lat)[0] == pytest.approx(0, abs=1e-4)  # perfect


def test_polar_southern_hemisphere_and_bad_input():
    points = [(h, -d) for h, d in three_points(0.0, 89.5)]  # mirror image around the south pole
    total, alt, az = pointing.polar_error(points, -31.0)
    assert total == pytest.approx(30, abs=0.01)
    with pytest.raises(ValueError, match="too close"):
        pointing.ra_axis([(10.0, 70.0)] * 3)
