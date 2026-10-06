"""The observatory: devices, guarded actions and the safety supervisor.

Devices are ASCOM-style objects (alpyca's Alpaca clients, or INDI adapters exposing the same
names: Connected, SlewToCoordinatesAsync, Slewing, Park, AtPark, Tracking, RightAscension,
Declination, StartExposure, ImageReady, ImageArray, CloseShutter, IsSafe, ...).

Every slew goes through slew(), which checks the safety rules first. The supervisor thread
runs in this process (the observatory process, not the UI) and on any unsafe condition:
aborts the running exposure, stops the sequence, parks the mount and closes the dome; each
step is tried on its own, so one failing device does not stop the others.
"""

import threading
import time
from collections import deque
from datetime import UTC, datetime

import astropy.units as u
from astropy.coordinates import TETE, AltAz, SkyCoord
from astropy.time import Time

from .safety import Rules, check_link, check_sun, check_target, check_weather


class SafetyError(RuntimeError):
    pass


class DeviceError(RuntimeError):
    pass


class Observatory:
    def __init__(self, location, rules: Rules | None = None, clock=time.monotonic, now=Time.now, **devices):
        self.location = location
        self.rules = rules or Rules()
        self.clock, self.now = clock, now
        self.devices = {k: v for k, v in devices.items() if v is not None}  # mount, camera, filterwheel, ...
        self.last_ok = {k: clock() for k in self.devices}
        self.log = deque(maxlen=1000)
        self.lock = threading.RLock()  # one device command at a time
        self.abort = threading.Event()  # set when unsafe: sequences stop at the next check
        self.reasons: list[str] = []
        self.last_check = None  # clock() of the last completed safety check (the window shows a stale one)
        self.interval_s = 5.0
        self._failures = {}  # error text -> clock() of its last log line, so a failing rule does not flood the log
        self._stop = threading.Event()
        self._thread = None

    # --- device access ------------------------------------------------------
    def note(self, text):
        self.log.append(f"{datetime.now(UTC).isoformat(timespec='seconds')} {text}")

    def call(self, name, attr, *args):
        """Read an attribute or call a method of a device; records the time of the last good answer."""
        dev = self.devices.get(name)
        if dev is None:
            raise DeviceError(f"no {name} connected")
        with self.lock:
            try:
                value = getattr(dev, attr)
                result = value(*args) if callable(value) else value
            except Exception as e:
                raise DeviceError(f"{name}.{attr}: {type(e).__name__}: {e}") from e
        self.last_ok[name] = self.clock()
        return result

    def set(self, name, attr, value):
        with self.lock:
            try:
                setattr(self.devices[name], attr, value)
            except Exception as e:
                raise DeviceError(f"{name}.{attr} = {value!r}: {type(e).__name__}: {e}") from e
        self.last_ok[name] = self.clock()

    # --- coordinates in the mount's system -------------------------------------
    def _topocentric(self):
        try:
            return self.call("mount", "EquatorialSystem") in (1, "equTopocentric")
        except DeviceError:
            return True  # most mounts use JNow; a few arcmin either way never matters for safety

    def _to_mount(self, coord: SkyCoord, t: Time):
        c = coord.transform_to(TETE(obstime=t, location=self.location)) if self._topocentric() else coord.icrs
        return c.ra.hour, c.dec.deg

    def mount_position(self) -> SkyCoord:
        ra, dec = self.call("mount", "RightAscension"), self.call("mount", "Declination")
        t = self.now()
        if self._topocentric():
            return SkyCoord(ra * u.hourangle, dec * u.deg, frame=TETE(obstime=t, location=self.location)).icrs
        return SkyCoord(ra * u.hourangle, dec * u.deg)

    # --- guarded actions --------------------------------------------------------
    def slew(self, coord: SkyCoord, timeout_s=300, poll_s=0.5):
        if self.reasons:
            raise SafetyError("observatory is unsafe: " + "; ".join(self.reasons))
        t = self.now()
        try:
            reasons = check_target(coord, t, self.location, self.rules)
        except Exception as e:
            first = (str(e).strip().splitlines() or [type(e).__name__])[0]
            self.note(f"slew refused: cannot evaluate the safety rules: {first}")
            raise SafetyError(f"cannot evaluate the safety rules ({first}): the telescope was not moved") from e
        if reasons:
            self.note("slew refused: " + "; ".join(reasons))
            raise SafetyError("; ".join(reasons))
        if self.call("mount", "AtPark"):
            self.call("mount", "Unpark")
        try:
            self.set("mount", "Tracking", True)
        except DeviceError:
            pass  # mounts that cannot switch tracking track anyway
        ra, dec = self._to_mount(coord, t)
        self.note(f"slew to {coord.to_string('hmsdms', precision=0)}")
        self.call("mount", "SlewToCoordinatesAsync", ra, dec)
        start = self.clock()
        while self.call("mount", "Slewing"):
            if self.abort.is_set():
                self.call("mount", "AbortSlew")
                raise SafetyError("slew aborted: " + "; ".join(self.reasons))
            if self.clock() - start > timeout_s:
                self.call("mount", "AbortSlew")
                raise DeviceError("slew did not finish in time")
            time.sleep(poll_s)

    def park(self):
        self.note("park mount")
        if self.call("mount", "Slewing"):
            self.call("mount", "AbortSlew")
        self.call("mount", "Park")

    # --- supervisor ---------------------------------------------------------------
    def _weather(self):
        is_safe = None
        if "monitor" in self.devices:
            try:
                is_safe = bool(self.call("monitor", "IsSafe"))
            except DeviceError:
                is_safe = "error"
        cond = {}
        if "conditions" in self.devices:
            for key, attr in (
                ("humidity", "Humidity"),
                ("windspeed", "WindSpeed"),
                ("rainrate", "RainRate"),
                ("cloudcover", "CloudCover"),
            ):
                try:
                    cond[key] = float(self.call("conditions", attr))
                except DeviceError as e:
                    cond[key] = None if "NotImplemented" in str(e) else "error"
        return is_safe, cond

    def _rule(self, name, function) -> list[str]:
        """One safety rule; a rule that raises is itself a reason (fail closed: an unknown state is unsafe)."""
        try:
            return function()
        except Exception as e:
            first = (str(e).strip().splitlines() or [type(e).__name__])[0]
            return [f"safety check {name} failed: {first}"]

    def _mount_rules(self):
        reasons = []
        try:
            parked = self.call("mount", "AtPark")
            if not parked:
                reasons += check_sun(self.mount_position(), self.now(), self.location, self.rules)
            if not parked and self.call("mount", "Tracking"):
                t = self.now()
                aa = self.mount_position().transform_to(AltAz(obstime=t, location=self.location))
                if aa.alt.deg < self.rules.horizon_alt(aa.az.deg) - 2:  # 2 deg grace for tracking past a limit
                    reasons.append(f"telescope is at altitude {aa.alt.deg:.1f} deg, below the limit")
        except DeviceError:
            pass  # covered by the link check
        return reasons

    def check(self) -> list[str]:
        """Everything that is unsafe right now (empty list = safe). Every rule runs on its own: one that fails
        does not hide the others, and is a reason itself."""
        for name in self.devices:  # refresh the link times
            try:
                self.call(name, "Connected")
            except DeviceError:
                pass
        reasons = self._rule("weather", lambda: check_weather(*self._weather(), self.rules))
        reasons += self._rule(
            "links", lambda: check_link({k: self.clock() - v for k, v in self.last_ok.items()}, self.rules)
        )
        if "mount" in self.devices:
            reasons += self._rule("sun and altitude", self._mount_rules)
        return reasons

    def make_safe(self, reasons):
        """Abort the exposure, stop sequences, park the mount, close the dome. Never raises."""
        self.abort.set()
        self.note("UNSAFE: " + "; ".join(reasons))
        steps = (
            ("camera", lambda: self.call("camera", "AbortExposure")),
            ("mount", self.park),
            ("dome", lambda: self.call("dome", "CloseShutter")),
            ("dome", lambda: self.call("dome", "Park")),
        )
        for name, action in steps:
            if name in self.devices:
                try:
                    action()
                except Exception as e:  # keep going: the other devices must still be made safe
                    self.note(f"safety action on {name} failed: {e}")

    def _parked(self):
        try:
            return "mount" not in self.devices or bool(self.call("mount", "AtPark"))
        except DeviceError:
            return False

    def supervise_once(self):
        try:
            reasons = self.check()
        except Exception as e:  # check() guards each rule; this is the last line of defence
            reasons = [f"safety check failed: {(str(e).strip().splitlines() or [type(e).__name__])[0]}"]
        if reasons and (reasons != self.reasons or not self._parked()):  # repeat until the mount is parked
            self.make_safe(reasons)
        elif not reasons and self.reasons:
            self.note("conditions safe again (manual restart needed)")
        self.reasons = reasons
        self.last_check = self.clock()
        return reasons

    def resume(self):
        """Clear the abort after an unsafe period; refused while anything is still unsafe."""
        reasons = self.check()
        if reasons:
            raise SafetyError("still unsafe: " + "; ".join(reasons))
        self.reasons = []
        self.abort.clear()
        self.note("resumed by the operator")

    def _supervisor_failed(self, error):
        """supervise_once itself failed: make safe anyway (an unknown state is unsafe), and log each distinct
        error at most every ten minutes."""
        text = f"safety check failed: {(str(error).strip().splitlines() or [type(error).__name__])[0]}"
        if self.clock() - self._failures.get(text, -1e9) > 600:
            self._failures[text] = self.clock()
            self.note(f"supervisor error: {text}")
        try:
            if text not in self.reasons or not self._parked():
                self.make_safe([text])
            self.reasons = [text]
        except Exception as e:  # make_safe never raises; this guards against a future change
            self.note(f"supervisor could not make the observatory safe: {e}")

    def start_supervisor(self, interval_s=5.0):
        self.interval_s = interval_s

        def loop():
            while not self._stop.wait(interval_s):
                try:
                    self.supervise_once()
                except Exception as e:  # the supervisor must never die, and never stay silent
                    self._supervisor_failed(e)

        self._stop.clear()
        self._thread = threading.Thread(target=loop, name="safety-supervisor", daemon=True)
        self._thread.start()

    def stop_supervisor(self):
        self._stop.set()
        if self._thread:
            self._thread.join(5)
