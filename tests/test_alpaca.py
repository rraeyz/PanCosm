"""The real Alpaca client (alpyca) against a minimal Alpaca HTTP device server (ASCOM Alpaca API v1)."""

import json
import threading
import warnings
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import pytest
from test_observatory import NIGHT, at

from astrowb.devices.server import build

STATE = {
    "telescope": {
        "connected": False,
        "rightascension": 0.0,
        "declination": 90.0,
        "atpark": True,
        "tracking": False,
        "slewing": False,
        "equatorialsystem": 1,
    },
    "safetymonitor": {"connected": False, "issafe": True},
}
CALLS = []


class AlpacaHandler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _answer(self, value=None, error=0, message=""):
        q = parse_qs(urlparse(self.path).query)
        body = {
            "ErrorNumber": error,
            "ErrorMessage": message,
            "ServerTransactionID": 1,
            "ClientTransactionID": int(q.get("ClientTransactionID", [0])[0]),
        }
        if value is not None:
            body["Value"] = value
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _parts(self):
        p = urlparse(self.path).path.strip("/").split("/")  # api, v1, type, number, member
        return p[2], p[4]

    def do_GET(self):
        if self.path.startswith("/management/v1/configureddevices"):  # what discovery lists
            return self._answer(
                [
                    {"DeviceName": "Sim mount", "DeviceType": "Telescope", "DeviceNumber": 0, "UniqueID": "a"},
                    {
                        "DeviceName": "Sim cloud sensor",
                        "DeviceType": "SafetyMonitor",
                        "DeviceNumber": 0,
                        "UniqueID": "b",
                    },
                    {"DeviceName": "Sim switch", "DeviceType": "Switch", "DeviceNumber": 0, "UniqueID": "c"},
                ]
            )
        kind, member = self._parts()
        CALLS.append(("GET", kind, member))
        if member in STATE[kind]:
            return self._answer(STATE[kind][member])
        self._answer(None, 0x400, "not implemented")

    def do_PUT(self):
        kind, member = self._parts()
        form = {
            k.lower(): v[0] for k, v in parse_qs(self.rfile.read(int(self.headers["Content-Length"])).decode()).items()
        }
        CALLS.append(("PUT", kind, member, form))
        s = STATE[kind]
        if member in ("connected", "tracking"):
            s[member] = form[member] == "True"
        elif member == "unpark":
            s["atpark"] = False
        elif member == "park":
            s["atpark"], s["tracking"] = True, False
        elif member == "slewtocoordinatesasync":
            s["rightascension"], s["declination"] = float(form["rightascension"]), float(form["declination"])
        self._answer()


@pytest.fixture
def alpaca_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), AlpacaHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def test_observatory_over_alpaca(alpaca_server):
    warnings.simplefilter("ignore")
    config = {
        "site": {"lat": 36.82, "lon": 30.34, "height": 2500},
        "devices": {"mount": {"alpaca": alpaca_server}, "monitor": {"alpaca": alpaca_server}},
    }
    obs, guider = build(config)
    obs.now = lambda: NIGHT
    assert STATE["telescope"]["connected"] and STATE["safetymonitor"]["connected"] and guider is None
    target = at(60, 120)
    obs.slew(target, poll_s=0)
    assert not STATE["telescope"]["atpark"] and STATE["telescope"]["tracking"]
    assert obs.mount_position().separation(target).arcsec < 1
    assert obs.supervise_once() == []
    STATE["safetymonitor"]["issafe"] = False
    assert obs.supervise_once() == ["safety monitor reports unsafe"]
    assert STATE["telescope"]["atpark"]  # parked over the network
    assert any(c[:3] == ("PUT", "telescope", "park") for c in CALLS)
