import warnings

import astropy.units as u
import numpy as np
import pytest
from astropy.coordinates import TETE, AltAz, EarthLocation, SkyCoord
from astropy.time import Time
from fake_devices import FakeCamera, FakeDome, FakeMonitor, FakeMount

from astrowb.devices.observatory import Observatory, SafetyError
from astrowb.devices.safety import Rules

SITE = EarthLocation.from_geodetic(30.34 * u.deg, 36.82 * u.deg, 2500 * u.m)
NIGHT = Time("2026-11-15T22:00:00")


@pytest.fixture(autouse=True)
def quiet():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        yield


class Clock:
    t = 1000.0

    def __call__(self):
        return self.t


@pytest.fixture
def obs():
    clock = Clock()
    o = Observatory(
        SITE,
        Rules(),
        clock=clock,
        now=lambda: NIGHT,
        mount=FakeMount(),
        dome=FakeDome(),
        monitor=FakeMonitor(),
        camera=FakeCamera(),
    )
    o.test_clock = clock
    return o


def at(alt, az):
    return SkyCoord(AltAz(alt=alt * u.deg, az=az * u.deg, obstime=NIGHT, location=SITE)).icrs


def test_slew_goes_to_the_right_place(obs):
    target = at(60, 120)
    obs.slew(target, poll_s=0)
    pos = obs.mount_position()
    assert pos.separation(target).arcsec < 1  # JNow round trip
    assert obs.devices["mount"].Tracking and not obs.devices["mount"].AtPark


def test_unsafe_slews_refused(obs):
    with pytest.raises(SafetyError, match="below the limit"):
        obs.slew(at(5, 200), poll_s=0)
    assert obs.devices["mount"].AtPark  # never moved
    assert "slew refused" in obs.log[-1]


def test_weather_unsafe_parks_and_closes(obs):
    obs.slew(at(60, 120), poll_s=0)
    assert obs.supervise_once() == []
    obs.devices["monitor"].IsSafe = False
    reasons = obs.supervise_once()
    assert reasons == ["safety monitor reports unsafe"]
    m, d, c = obs.devices["mount"], obs.devices["dome"], obs.devices["camera"]
    assert m.AtPark and d.closed == 1 and c.aborted == 1 and obs.abort.is_set()
    with pytest.raises(SafetyError, match="unsafe"):
        obs.slew(at(60, 120), poll_s=0)
    obs.devices["monitor"].IsSafe = True
    obs.supervise_once()
    obs.resume()
    assert not obs.abort.is_set()


def test_lost_link_triggers_safe_state_and_others_still_act(obs):
    obs.slew(at(60, 120), poll_s=0)
    obs.devices["camera"].broken = True  # camera dies; mount and dome must still be made safe
    obs.test_clock.t += 31
    reasons = obs.supervise_once()
    assert any("camera has not answered" in r for r in reasons)
    assert obs.devices["mount"].AtPark and obs.devices["dome"].closed == 1
    assert any("safety action on camera failed" in line for line in obs.log)


def test_park_retried_until_it_works(obs):
    obs.slew(at(60, 120), poll_s=0)
    obs.devices["monitor"].IsSafe = False
    mount = obs.devices["mount"]
    mount.broken = True
    obs.supervise_once()
    mount.broken = False
    obs.supervise_once()  # same reasons, but not parked yet: try again
    assert mount.AtPark


def test_tracking_below_horizon_is_unsafe(obs):
    obs.slew(at(60, 120), poll_s=0)
    low = at(5, 250).transform_to(TETE(obstime=NIGHT, location=SITE))
    obs.devices["mount"].RightAscension, obs.devices["mount"].Declination = low.ra.hour, low.dec.deg
    assert any("below the limit" in r for r in obs.supervise_once())
    assert obs.devices["mount"].AtPark


def test_resume_refused_while_unsafe(obs):
    obs.devices["monitor"].IsSafe = False
    obs.supervise_once()
    with pytest.raises(SafetyError, match="still unsafe"):
        obs.resume()


def test_sequence_writes_calibration_ready_frames(obs, tmp_path):
    from fake_devices import FakeFilterWheel

    from astrowb.calibration.frames import scan
    from astrowb.devices.sequence import Exposure, Target, run

    obs.devices["filterwheel"] = FakeFilterWheel()
    obs.last_ok["filterwheel"] = obs.clock()

    class Guider:
        dithers = 0

        def guide(self):
            pass

        def dither(self):
            Guider.dithers += 1

    seq = [
        Target("HAT-P-32", at(60, 120), [Exposure(0.01, 3, "V")], dither_every=2),
        Target("darks", None, [Exposure(0.01, 2, kind="dark"), Exposure(0.0, 2, kind="bias")]),
    ]
    paths = run(obs, seq, tmp_path, guider=Guider())
    assert len(paths) == 7 and Guider.dithers == 1
    frames, problems = scan(tmp_path)
    assert not problems
    kinds = sorted(f.kind for f in frames)
    assert kinds == ["bias"] * 2 + ["dark"] * 2 + ["light"] * 3
    light = next(f for f in frames if f.kind == "light")
    assert light.filter == "V" and light.temperature == -10.0 and light.shape == (40, 50)
    assert obs.devices["filterwheel"].Position == 2


def test_sequence_stops_when_unsafe(obs, tmp_path):
    from astrowb.devices.sequence import Exposure, Target, run

    obs.slew(at(60, 120), poll_s=0)
    obs.devices["monitor"].IsSafe = False
    obs.supervise_once()
    with pytest.raises(SafetyError):
        run(obs, [Target("x", None, [Exposure(0.01, 5, kind="dark")])], tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_autofocus_finds_best_position(obs):
    from fake_devices import FakeFocuser, FocusCamera

    from astrowb.devices.focus import autofocus

    foc = FakeFocuser(5000)
    obs.devices["focuser"], obs.devices["camera"] = foc, FocusCamera(foc, best=5130)
    report = autofocus(obs, exptime=0.01, step=60, n_steps=9, settle_s=0)
    assert abs(report["best"] - 5130) < 10 and foc.Position == report["best"]
    assert sum(n >= 5 for n in report["stars"]) >= 5  # far from focus, stars smear out: expected


def test_autofocus_refuses_without_stars(obs):
    from fake_devices import FakeFocuser

    from astrowb.devices.focus import autofocus

    foc = FakeFocuser(5000)
    obs.devices["focuser"] = foc  # FakeCamera images have no stars
    with pytest.raises(ValueError, match="too few"):
        autofocus(obs, exptime=0.01, settle_s=0)
    assert foc.Position == 5000  # back where it was


def test_meridian_flip_during_sequence(obs, tmp_path, monkeypatch):
    from astrowb.devices import focus, sequence

    obs.devices["mount"].SideOfPier = 0  # a German mount
    target = at(70, 180)
    ha = iter([-0.05, -0.02, 0.15, 0.2, 0.3])  # east of the meridian at the slew, then crossing it
    monkeypatch.setattr(focus, "hour_angle", lambda o, c: next(ha))
    monkeypatch.setattr(sequence, "hour_angle", focus.hour_angle)
    slews = []
    real_slew = obs.slew
    obs.slew = lambda coord, poll_s=0.5: (slews.append(coord), real_slew(coord, poll_s=0))
    sequence.run(obs, [sequence.Target("t", target, [sequence.Exposure(0.01, 4)])], tmp_path)
    assert len(slews) == 2  # the slew and exactly one flip


def test_hour_angle_sign(obs):
    from astrowb.devices.focus import hour_angle

    assert hour_angle(obs, at(60, 100)) < 0 < hour_angle(obs, at(60, 260))  # east negative, west positive


def test_sky_flats_follow_the_fading_twilight(obs, tmp_path):
    from fake_devices import FakeFilterWheel

    from astrowb.devices.sequence import sky_flats

    class Twilight(FakeCamera):  # sky rate halves every exposure (evening), bias 500 ADU
        @property
        def ImageArray(self):
            n, (t, _) = len(self.exposures), self.exposures[-1]
            level = 500 + 40000 * 0.8**n * t
            return np.full(self.shape, min(level, 65535), np.int32).T

    obs.devices["camera"], obs.devices["filterwheel"] = Twilight(), FakeFilterWheel()
    paths = sky_flats(obs, "V", 5, tmp_path, target_adu=20000, bias_adu=500, first_exp=0.5, max_exp=60)
    from astropy.io import fits

    assert len(paths) == 5
    for p in paths:
        h = fits.getheader(p)
        level = np.median(fits.getdata(p)) - 500
        assert h["IMAGETYP"] == "Flat Field" and h["FILTER"] == "V" and abs(level - 20000) <= 0.3 * 20000
    times = [fits.getheader(p)["EXPTIME"] for p in paths]
    assert times == sorted(times) and times[-1] > times[0]  # longer as the sky fades


def test_dawn_parks_an_unparked_telescope(obs):
    obs.slew(at(60, 120), poll_s=0)
    assert obs.supervise_once() == []
    obs.now = lambda: Time("2026-11-16T06:30:00")  # 08:30 local solar time: daylight
    reasons = obs.supervise_once()
    assert any("night is over" in r for r in reasons) and obs.devices["mount"].AtPark
    assert obs.devices["dome"].closed >= 1


def test_whole_night_time_series(obs, tmp_path):
    import astropy.units as u

    from astrowb.devices.sequence import Exposure, Target, run, tonight

    dusk, dawn = tonight(obs)
    assert dusk < NIGHT < dawn and 10 < (dawn - dusk).to_value("h") < 14
    clock = {"t": NIGHT}
    obs.now = lambda: clock["t"]
    cam = obs.devices["camera"]
    start_exposure = cam.StartExposure

    def exposing(duration, light):  # the camera takes real (simulated) time
        clock["t"] = clock["t"] + duration * u.s
        start_exposure(duration, light)

    cam.StartExposure = exposing
    target = Target("EB", at(60, 120), [Exposure(60.0, 2, "V")], start=NIGHT + 10 * u.min, end=NIGHT + 40 * u.min)
    paths = run(obs, [target], tmp_path, wait=lambda s: clock.__setitem__("t", clock["t"] + s * u.s))
    assert len(paths) == 30  # 30 one-minute frames fit between start and end, none beyond
    assert clock["t"] <= NIGHT + 40 * u.min
    late = Target("late", at(60, 120), [Exposure(60.0, 1)], end=NIGHT)
    assert run(obs, [late], tmp_path) == []  # window already over: skipped


def test_camera_settings_subframe_rotator_and_headers(obs, tmp_path):
    from astropy.io import fits
    from fake_devices import FakeRotator

    from astrowb.devices.sequence import Exposure, Target, run

    cam = obs.devices["camera"]
    cam.CameraXSize, cam.CameraYSize, cam.Offset, cam.ReadoutModes = 500, 400, 10, ["Normal", "Fast"]
    obs.devices["rotator"] = FakeRotator()
    obs.last_ok["rotator"] = obs.clock()
    exps = [Exposure(0.01, 1, gain=139, offset=21, readout=1, roi=[10, 20, 50, 40]), Exposure(0.01, 1, binning=2)]
    paths = run(obs, [Target("M 42", at(60, 120), exps, rotation=95.0)], tmp_path)
    h = fits.getheader(paths[0])
    assert (h["GAIN"], h["OFFSET"], h["READOUTM"], h["XORGSUBF"], h["YORGSUBF"]) == (139, 21, "Fast", 10, 20)
    assert h["ROTATANG"] == 95.0 and obs.devices["rotator"].moves == [95.0]
    assert (cam.StartX, cam.StartY, cam.NumX, cam.NumY) == (0, 0, 250, 200)  # second frame: full frame again
    assert "XORGSUBF" not in fits.getheader(paths[1])


def test_filter_focus_offsets_and_temperature_compensation(obs, tmp_path):
    from fake_devices import FakeFilterWheel, FakeFocuser

    from astrowb.devices.sequence import Exposure, Target, run

    wheel, focuser = FakeFilterWheel(), FakeFocuser(5000)
    focuser.Temperature = 10.0
    obs.devices |= {"filterwheel": wheel, "focuser": focuser}
    obs.focus = {"offsets": {"L": 0, "B": -30, "V": 15}, "temp_coeff": -6.0, "temp_step": 0.5}
    positions = []
    cam = obs.devices["camera"]
    start = cam.StartExposure

    def exposing(duration, light):
        positions.append(focuser.Position)
        focuser.Temperature -= 0.3  # cooling night
        start(duration, light)

    cam.StartExposure = exposing
    run(obs, [Target("x", at(60, 120), [Exposure(0.01, 2, "B"), Exposure(0.01, 2, "V")])], tmp_path)
    # L -> B: -30; B -> V: +45; before the third frame the focuser is 0.6 C cooler: -6 * -0.6 = +3.6 -> +4
    assert positions == [4970, 4970, 5019, 5019]


def test_panel_flats(obs, tmp_path):
    from fake_devices import FakeFilterWheel, FakePanel

    from astrowb.devices.sequence import panel_flats

    class Lit(FakeCamera):
        @property
        def ImageArray(self):
            t = self.exposures[-1][0]
            return np.full(self.shape, 500 + 8000 * t * (obs.devices["panel"].Brightness / 100), np.int32).T

    obs.devices |= {"camera": Lit(), "filterwheel": FakeFilterWheel(), "panel": FakePanel()}
    paths = panel_flats(obs, "R", 3, tmp_path, brightness=100, target_adu=20000, bias_adu=500)
    assert len(paths) == 3 and obs.devices["panel"].log == ["close", "on 100", "off"]
    paths = panel_flats(obs, "R", 1, tmp_path / "b", target_adu=20000, bias_adu=500, open_after=True)
    assert obs.devices["panel"].log[-3:] == ["on 255", "off", "open"]
