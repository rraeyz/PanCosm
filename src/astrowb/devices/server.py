"""The observatory process: owns the devices, the safety supervisor and running sequences, and
serves a small JSON API so the UI can run on the same computer or elsewhere.

The process keeps running (and keeps the observatory safe) if the UI closes or crashes.
Every request must carry "Authorization: Bearer <token>"; the server listens on 127.0.0.1 by
default — listening on other addresses is an explicit choice in the configuration (use a VPN or
an SSH tunnel across the internet: the API has no TLS of its own).

Configuration (JSON):
{
  "site": {"lat": 36.82, "lon": 30.34, "height": 2500},
  "rules": {"min_alt": 15, "horizon": [[0, 10], [90, 25]], ...},
  "devices": {"mount": {"alpaca": "192.168.1.20:11111", "number": 0},
              "camera": {"indi": "127.0.0.1:7624", "device": "CCD Simulator"}, "filterwheel": {...},
              "focuser": {...}, "dome": {...}, "monitor": {...}, "conditions": {...},
              "rotator": {...}, "panel": {...}},   (rotator and flat panel: Alpaca only)
  "focus": {"offsets": {"B": -30, "R": 12}, "temp_coeff": -5.0, "temp_step": 0.5},
  "phd2": {"host": "127.0.0.1", "port": 4400},
  "listen": "127.0.0.1:11112",
  "token": "a long random string"
}
"""

import hmac
import json
import os
import secrets
import shutil
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import astropy.units as u
from astropy.coordinates import AltAz, EarthLocation, SkyCoord

from .client import Client  # noqa: F401  (re-exported: the UI side used to import it from here)
from .focus import autofocus
from .observatory import Observatory
from .safety import Rules
from .sequence import Exposure, Target, run, sky_flats, tonight

ALPACA_CLASSES = {
    "mount": ("alpaca.telescope", "Telescope"),
    "camera": ("alpaca.camera", "Camera"),
    "filterwheel": ("alpaca.filterwheel", "FilterWheel"),
    "focuser": ("alpaca.focuser", "Focuser"),
    "dome": ("alpaca.dome", "Dome"),
    "monitor": ("alpaca.safetymonitor", "SafetyMonitor"),
    "conditions": ("alpaca.observingconditions", "ObservingConditions"),
    "rotator": ("alpaca.rotator", "Rotator"),
    "panel": ("alpaca.covercalibrator", "CoverCalibrator"),
}


def connect_alpaca(kind, address, number=0):
    import importlib

    module, cls = ALPACA_CLASSES[kind]
    device = getattr(importlib.import_module(module), cls)(address, number)
    device.Connected = True
    return device


def build(config: dict):
    """Observatory (connected, supervisor not started) and guider from a configuration dict."""
    site = config["site"]
    loc = EarthLocation.from_geodetic(site["lon"] * u.deg, site["lat"] * u.deg, site.get("height", 0) * u.m)
    devices, indi_clients = {}, {}
    for kind, spec in config.get("devices", {}).items():
        if "alpaca" in spec:
            devices[kind] = connect_alpaca(kind, spec["alpaca"], spec.get("number", 0))
        elif "indi" in spec:
            from .indi import ADAPTERS, IndiClient

            if spec["indi"] not in indi_clients:  # one connection per INDI server
                host, _, port = spec["indi"].rpartition(":")
                indi_clients[spec["indi"]] = IndiClient(host or "127.0.0.1", int(port or 7624))
            devices[kind] = ADAPTERS[kind](indi_clients[spec["indi"]], spec["device"])
    obs = Observatory(loc, Rules(**config.get("rules", {})), **devices)
    obs.focus = dict(config.get("focus", {}))  # filter offsets and temperature compensation (sequence.py)
    guider = None
    if config.get("phd2"):
        from .phd2 import PHD2

        guider = PHD2(config["phd2"].get("host", "127.0.0.1"), config["phd2"].get("port", 4400))
    return obs, guider


class Controller:
    """Long-running actions in threads, state for /status."""

    def __init__(self, obs: Observatory, guider=None):
        self.obs, self.guider = obs, guider
        self.job = {"running": False, "name": "", "progress": 0.0, "message": "", "written": [], "error": None}
        self.job["result"] = None
        self._thread = None
        self.solve = None  # solve(path, ra_deg, dec_deg) -> WCS header; the installed solver when None
        self.written = set()  # the only files /file hands out: frames this process saved

    def _start(self, name, fn):
        if self._thread and self._thread.is_alive():
            raise RuntimeError(f"busy with {self.job['name']}")
        self.job = {"running": True, "name": name, "progress": 0.0, "message": "", "written": [], "error": None}
        self.job["result"] = None

        def body():
            try:
                result = fn()
                if isinstance(result, dict):
                    self.job["result"] = result
                if isinstance(result, list):
                    self.job["written"] = result
                    self.written.update(str(p) for p in result)
            except Exception as e:  # reported to the UI; the supervisor keeps the observatory safe
                self.job["error"] = f"{type(e).__name__}: {e}"
                self.obs.note(f"{name} stopped: {e}")
            finally:
                self.job["running"] = False

        self._thread = threading.Thread(target=body, name=name, daemon=True)
        self._thread.start()

    def slew(self, ra_deg, dec_deg):
        self._start("slew", lambda: self.obs.slew(SkyCoord(ra_deg * u.deg, dec_deg * u.deg)))

    def _when(self, text):
        """ "dusk" / "dawn" (tonight, Sun at the safety limit) or an ISO time in UTC; None when empty."""
        from astropy.time import Time

        if not text:
            return None
        if text in ("dusk", "dawn"):
            dusk, dawn = tonight(self.obs)
            when = dusk if text == "dusk" else dawn
            if when is None:
                raise ValueError(f"no {text} tonight at this site")
            return when
        return Time(text, scale="utc")

    def sequence(self, spec):
        targets = []
        for t in spec["targets"]:
            coord = SkyCoord(t["ra"] * u.deg, t["dec"] * u.deg) if t.get("ra") is not None else None
            exposures = [Exposure(**e) for e in t["exposures"]]
            start, end = self._when(t.get("start")), self._when(t.get("end"))
            rotation = float(t["rotation"]) if t.get("rotation") not in (None, "") else None
            targets.append(Target(t["name"], coord, exposures, t.get("dither_every", 0), start, end, rotation))

        def progress(f, msg):
            self.job["progress"], self.job["message"] = f, msg

        if self.obs.abort.is_set():  # after an abort or unsafe period the operator resumes explicitly
            raise RuntimeError("aborted: resume first")
        self._start("sequence", lambda: run(self.obs, targets, spec["out_dir"], self.guider, progress))

    def sky_flats(self, spec):
        if self.obs.abort.is_set():
            raise RuntimeError("aborted: resume first")
        kwargs = {k: float(spec[k]) for k in ("target_adu", "bias_adu", "min_exp", "max_exp") if k in spec}
        self._start(
            "sky flats",
            lambda: sky_flats(self.obs, spec.get("filter"), int(spec["count"]), spec["out_dir"], **kwargs),
        )

    def panel_flats(self, spec):
        from .sequence import panel_flats

        if self.obs.abort.is_set():
            raise RuntimeError("aborted: resume first")
        kwargs = {k: float(spec[k]) for k in ("target_adu", "bias_adu", "min_exp", "max_exp") if k in spec}
        brightness = int(spec["brightness"]) if spec.get("brightness") not in (None, "") else None
        self._start(
            "panel flats",
            lambda: panel_flats(
                self.obs,
                spec.get("filter"),
                int(spec["count"]),
                spec["out_dir"],
                brightness,
                bool(spec.get("open_after")),
                **kwargs,
            ),
        )

    def _solved_centre(self, spec):
        """A function that exposes one frame, plate-solves it and returns the sky position of its centre."""
        from .. import astrometry
        from .pointing import image_centre
        from .sequence import expose, save

        exp = Exposure(float(spec.get("exptime", 5.0)), 1, None, int(spec.get("binning", 2)))
        folder = Path(spec["out_dir"]) / "pointing"
        solve = self.solve or (
            lambda path, ra, dec: astrometry.solve(path, ra_deg=ra, dec_deg=dec, radius_deg=10.0, timeout=120)
        )

        def take():
            hint = self.obs.mount_position()
            image, date_obs = expose(self.obs, exp)
            folder.mkdir(parents=True, exist_ok=True)
            path = save(self.obs, Target("pointing", None), exp, image, date_obs, folder, 1)
            return image_centre(solve(str(path), hint.ra.deg, hint.dec.deg), image.shape)

        return take

    def center(self, spec):
        """Slew, solve, sync and slew again until the target is in the middle of the image."""
        from .pointing import center

        if self.obs.abort.is_set():
            raise RuntimeError("aborted: resume first")
        target = SkyCoord(float(spec["ra"]) * u.deg, float(spec["dec"]) * u.deg)
        take = self._solved_centre(spec)
        tolerance = float(spec.get("tolerance", 30.0))
        self._start("centre", lambda: {"errors": center(self.obs, target, take, tolerance)})

    def polar(self, spec):
        """Polar alignment error from three solved frames while only the RA axis turns (by step degrees)."""
        from .pointing import hadec, polar_error

        if self.obs.abort.is_set():
            raise RuntimeError("aborted: resume first")
        take, step = self._solved_centre(spec), float(spec.get("step", 30.0))

        def body():
            start, points = self.obs.mount_position(), []
            for k in range(3):
                if k:
                    self.obs.slew(SkyCoord(start.ra - k * step * u.deg, start.dec))  # RA axis only
                points.append(hadec(take(), self.obs.now(), self.obs.location))
                self.job["progress"] = (k + 1) / 3
            total, alt, az = polar_error(points, self.obs.location.lat.deg)
            self.obs.note(f"polar alignment error {total:.1f} arcmin (altitude {alt:+.1f}, azimuth {az:+.1f})")
            return {"polar": {"total": total, "alt": alt, "az": az}}

        self._start("polar alignment", body)

    def preview(self, spec):
        """One frame (not part of a sequence), saved in out_dir/preview for framing and focusing."""
        from pathlib import Path

        from .sequence import expose, save, set_filter

        if self.obs.abort.is_set():
            raise RuntimeError("aborted: resume first")
        exp = Exposure(float(spec.get("exptime", 1.0)), 1, spec.get("filter"), int(spec.get("binning", 1)))

        def body():
            set_filter(self.obs, exp.filter)
            image, date_obs = expose(self.obs, exp)
            target = Target(spec.get("name") or "preview", None)
            folder = Path(spec["out_dir"]) / "preview"
            folder.mkdir(parents=True, exist_ok=True)
            return [str(save(self.obs, target, exp, image, date_obs, folder, 1))]

        self._start("preview", body)

    def cooler(self, spec):
        cam = "camera"
        if "temperature" in spec:
            self.obs.set(cam, "SetCCDTemperature", float(spec["temperature"]))
        if "on" in spec:
            self.obs.set(cam, "CoolerOn", bool(spec["on"]))
        self.obs.note(f"cooler: {spec}")

    def focus_to(self, position):
        self.obs.call("focuser", "Move", int(position))

    def filter_to(self, name):
        from .sequence import set_filter

        self._start("filter", lambda: set_filter(self.obs, name))

    def abort(self):
        self.obs.abort.set()  # sequences and slews stop at their next check
        self.obs.note("abort requested by the operator")

    def status(self):
        obs = self.obs
        out = {
            "safe": not obs.reasons,
            "reasons": obs.reasons,
            "aborted": obs.abort.is_set(),
            # seconds since the supervisor last finished a check (None: not running); the window warns when stale
            "checked_s_ago": None if obs.last_check is None else round(obs.clock() - obs.last_check, 1),
            "check_interval_s": obs.interval_s,
            "job": self.job,
            "devices": {k: round(obs.clock() - v, 1) for k, v in obs.last_ok.items()},
            "log": list(obs.log)[-50:],
        }
        for name, attrs in (
            ("camera", ("CCDTemperature", "CoolerOn", "CoolerPower", "SetCCDTemperature")),
            ("focuser", ("Position", "IsMoving", "Temperature")),
            ("filterwheel", ("Position", "Names")),
            ("rotator", ("Position", "IsMoving")),
        ):
            if name in obs.devices:
                state = {}
                for attr in attrs:
                    try:
                        v = obs.call(name, attr)
                        state[attr] = list(v) if attr == "Names" else v
                    except Exception:  # optional property, or device not answering (the link check reports it)
                        pass
                out[name] = state
        if "mount" in obs.devices:
            try:
                pos = obs.mount_position()
                aa = pos.transform_to(AltAz(obstime=obs.now(), location=obs.location))
                out["mount"] = {
                    "ra": pos.ra.deg,
                    "dec": pos.dec.deg,
                    "alt": aa.alt.deg,
                    "az": aa.az.deg,
                    "parked": bool(obs.call("mount", "AtPark")),
                    "tracking": bool(obs.call("mount", "Tracking")),
                }
            except Exception as e:
                out["mount"] = {"error": str(e)}
        return out


MAX_WRONG = 10  # wrong tokens in a row from one address before it is locked out (ARC-22)
LOCK_S = 300.0  # how long the lock-out lasts


class _Guard:
    """The token check with a lock-out per address (ARC-22)."""

    def __init__(self, token):
        self.expected = f"Bearer {token}".encode()
        self.wrong, self.lock = {}, threading.Lock()  # address -> (wrong tokens in a row, locked until)

    def check(self, address, given):
        """None when the request may go on, else (HTTP code, error text)."""
        now = time.monotonic()
        with self.lock:
            count, until = self.wrong.get(address, (0, 0.0))
        if until > now:  # guessing the token: every request is refused for a while, the right one too
            return 429, f"too many wrong tokens; try again in {until - now:.0f} s"
        if hmac.compare_digest(given.encode(), self.expected):
            with self.lock:
                self.wrong.pop(address, None)
            return None
        count += 1
        with self.lock:
            self.wrong[address] = (0, now + LOCK_S) if count >= MAX_WRONG else (count, 0.0)
        return 401, "missing or wrong token"


def make_handler(ctrl: Controller, token: str):
    guard = _Guard(token)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # no console noise; the observatory log has the events
            pass

        def _reply(self, code, obj):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _authorised(self):
            if refused := guard.check(self.client_address[0], self.headers.get("Authorization", "")):
                self._reply(refused[0], {"error": refused[1]})
            return not refused

        def do_GET(self):
            if not self._authorised():
                return
            url = urllib.parse.urlsplit(self.path)
            if url.path == "/status":
                self._reply(200, ctrl.status())
            elif url.path == "/file":
                self._send_file(urllib.parse.parse_qs(url.query).get("path", [""])[0])
            else:
                self._reply(404, {"error": "unknown path"})

        def _send_file(self, path):
            if path not in ctrl.written or not os.path.isfile(path):
                return self._reply(404, {"error": "not a frame written by the observatory"})
            self.send_response(200)
            self.send_header("Content-Type", "application/fits")
            self.send_header("Content-Length", str(os.path.getsize(path)))
            self.end_headers()
            with open(path, "rb") as f:
                shutil.copyfileobj(f, self.wfile)

        def do_POST(self):
            if not self._authorised():
                return
            try:
                length = int(self.headers.get("Content-Length", 0))
                if length > 1_000_000:
                    raise ValueError("request too large")
                body = json.loads(self.rfile.read(length) or b"{}")
                actions = {
                    "/slew": lambda: ctrl.slew(float(body["ra"]), float(body["dec"])),
                    "/park": lambda: ctrl._start("park", ctrl.obs.park),
                    "/abort": ctrl.abort,
                    "/resume": ctrl.obs.resume,
                    "/sequence": lambda: ctrl.sequence(body),
                    "/skyflats": lambda: ctrl.sky_flats(body),
                    "/panelflats": lambda: ctrl.panel_flats(body),
                    "/preview": lambda: ctrl.preview(body),
                    "/cooler": lambda: ctrl.cooler(body),
                    "/focuser": lambda: ctrl.focus_to(body["position"]),
                    "/filter": lambda: ctrl.filter_to(body["name"]),
                    "/center": lambda: ctrl.center(body),
                    "/polar": lambda: ctrl.polar(body),
                    "/autofocus": lambda: ctrl._start(
                        "autofocus",
                        lambda: autofocus(
                            ctrl.obs,
                            float(body.get("exptime", 2.0)),
                            int(body.get("step", 50)),
                            int(body.get("n_steps", 9)),
                        ),
                    ),
                }
                if self.path not in actions:
                    return self._reply(404, {"error": "unknown path"})
                actions[self.path]()
                self._reply(200, {"ok": True})
            except Exception as e:  # bad input or refused action: tell the client why
                self._reply(400, {"error": f"{type(e).__name__}: {e}"})

    return Handler


def serve(ctrl: Controller, token: str, host="127.0.0.1", port=11112, tls=None):
    """Start the API server in a thread; returns the server (call .shutdown() to stop).
    tls: (certificate, key) files for HTTPS."""
    server = ThreadingHTTPServer((host, port), make_handler(ctrl, token))
    if tls:
        from .tls import server_context

        server.socket = server_context(*tls).wrap_socket(server.socket, server_side=True)
    threading.Thread(target=server.serve_forever, name="observatory-api", daemon=True).start()
    return server


def main(config_path):
    """Entry point of the observatory process (`--observatory config.json`)."""
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    token = config.get("token") or secrets.token_urlsafe(24)
    host, _, port = config.get("listen", "127.0.0.1:11112").rpartition(":")
    obs, guider = build(config)
    obs.start_supervisor(config.get("supervisor_interval_s", 5.0))
    tls, scheme = None, "http"
    if config.get("tls"):
        from .tls import ensure_certificate

        cert, key, fp = ensure_certificate(Path(config_path).parent)
        tls, scheme = (cert, key), "https"
        print(f"certificate fingerprint (SHA-256): {fp}", flush=True)
    server = serve(Controller(obs, guider), token, host, int(port), tls)
    print(f"observatory API on {scheme}://{host}:{port}  token: {token}", flush=True)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        server.shutdown()
        obs.stop_supervisor()
