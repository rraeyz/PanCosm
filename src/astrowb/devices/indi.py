"""INDI client (XML over TCP, protocol 1.7) and adapters with the ASCOM-style names the
observatory uses, so INDI and Alpaca devices are interchangeable.

Written from the INDI protocol specification (Downey 2007, indilib.org): the client sends
<getProperties/>; the server defines vectors (defNumberVector, defSwitchVector, defTextVector,
defLightVector, defBLOBVector) and updates them (set...Vector); the client changes them with
new...Vector. Images arrive as base64 FITS in BLOBs after <enableBLOB>Also</enableBLOB>.
"""

import base64
import io
import socket
import threading
import time
import xml.etree.ElementTree as ET

import numpy as np


class IndiError(RuntimeError):
    pass


class IndiClient:
    def __init__(self, host="127.0.0.1", port=7624, timeout=10.0):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.sock.settimeout(None)
        self.props = {}  # (device, name) -> {"kind", "state", "values": {element: value}, "perm"}
        self.blobs = {}  # (device, name) -> (time, bytes, format)
        self.cond = threading.Condition()
        self.alive = True
        self._parser = ET.XMLPullParser(events=("end",))
        self._parser.feed(b"<stream>")  # INDI is a stream of top-level elements
        threading.Thread(target=self._reader, name="indi-reader", daemon=True).start()
        self.send('<getProperties version="1.7"/>')

    def send(self, xml: str):
        self.sock.sendall(xml.encode())

    def close(self):
        self.alive = False
        try:
            self.sock.close()
        except OSError:
            pass

    def _reader(self):
        try:
            while self.alive:
                data = self.sock.recv(65536)
                if not data:
                    break
                self._parser.feed(data)
                for _, el in self._parser.read_events():
                    if el.tag.startswith(("def", "set", "del")) and el.tag.endswith("Vector"):
                        self._handle(el)
                        el.clear()
        except (OSError, ET.ParseError):
            pass
        finally:
            self.alive = False
            with self.cond:
                self.cond.notify_all()

    def _handle(self, el):
        key = (el.get("device"), el.get("name"))
        kind = el.tag[3:-6]  # Number, Switch, Text, Light, BLOB
        with self.cond:
            if el.tag.startswith("del"):
                self.props.pop(key, None)
            else:
                prop = self.props.setdefault(key, {"kind": kind, "state": "Idle", "values": {}, "perm": "rw"})
                prop["state"] = el.get("state", prop["state"])
                prop["perm"] = el.get("perm", prop["perm"])
                for child in el:
                    name = child.get("name")
                    text = (child.text or "").strip()
                    if kind == "Number":
                        prop["values"][name] = _number(text)
                    elif kind == "BLOB" and el.tag.startswith("set") and text:
                        self.blobs[key] = (time.monotonic(), base64.b64decode(text), child.get("format", ""))
                    else:
                        prop["values"][name] = text
            self.cond.notify_all()

    def get(self, device, name, timeout=10.0):
        """A property; waits for it only while the device has not defined its properties yet."""
        with self.cond:
            if any(d == device for d, _ in self.props):
                timeout = min(timeout, 0.5)  # the device is known: a missing property is really missing
        deadline = time.monotonic() + timeout
        with self.cond:
            while (device, name) not in self.props:
                if not self.alive or not self.cond.wait(max(0.0, deadline - time.monotonic())):
                    raise IndiError(f"{device}: property {name} not available")
            return self.props[(device, name)]

    def has(self, device, name):
        with self.cond:
            return (device, name) in self.props

    def wait_state(self, device, name, states=("Ok", "Idle"), timeout=60.0):
        deadline = time.monotonic() + timeout
        with self.cond:
            while self.props.get((device, name), {}).get("state") not in states:
                if not self.alive or not self.cond.wait(max(0.0, deadline - time.monotonic())):
                    raise IndiError(f"{device}: {name} did not reach {states}")
            return self.props[(device, name)]

    def new(self, device, name, values: dict):
        prop = self.get(device, name)
        kind = prop["kind"]
        with self.cond:
            prop["state"] = "Busy"  # INDI convention: Busy until the driver answers with set...Vector
        body = "".join(f'<one{kind} name="{_esc(k)}">{_esc(_fmt(v))}</one{kind}>' for k, v in values.items())
        self.send(f'<new{kind}Vector device="{_esc(device)}" name="{_esc(name)}">{body}</new{kind}Vector>')

    def switch(self, device, name, element):
        self.new(device, name, {element: "On"})

    def enable_blobs(self, device):
        self.send(f'<enableBLOB device="{_esc(device)}">Also</enableBLOB>')


def _number(text):
    try:
        if ":" in text or " " in text.strip():  # sexagesimal
            parts = [float(p) for p in text.replace(":", " ").split()]
            sign = -1 if text.strip().startswith("-") else 1
            return sign * (abs(parts[0]) + sum(p / 60**i for i, p in enumerate(parts[1:], 1)))
        return float(text)
    except ValueError:
        return float("nan")


def _fmt(v):
    if isinstance(v, bool):
        return "On" if v else "Off"
    return repr(float(v)) if isinstance(v, (int, float)) else str(v)


def _esc(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


class _Device:
    def __init__(self, client: IndiClient, device: str):
        self.client, self.device = client, device
        prop = client.get(device, "CONNECTION")
        if prop["values"].get("CONNECT") != "On":
            client.switch(device, "CONNECTION", "CONNECT")
            client.wait_state(device, "CONNECTION", timeout=30)

    def _value(self, name, element):
        return self.client.get(self.device, name)["values"][element]

    def _optional(self, name, element):
        """A property that not every driver has: fail at once instead of waiting for it."""
        if not self.client.has(self.device, name):
            raise IndiError(f"{self.device} has no {name}")
        return self._value(name, element)

    @property
    def Connected(self):
        if not self.client.alive:
            raise IndiError("INDI server connection lost")
        return self._value("CONNECTION", "CONNECT") == "On"

    @Connected.setter
    def Connected(self, value):
        self.client.switch(self.device, "CONNECTION", "CONNECT" if value else "DISCONNECT")


class IndiTelescope(_Device):
    EquatorialSystem = 1  # INDI EQUATORIAL_EOD_COORD is JNow

    @property
    def RightAscension(self):
        return self._value("EQUATORIAL_EOD_COORD", "RA")

    @property
    def Declination(self):
        return self._value("EQUATORIAL_EOD_COORD", "DEC")

    def SlewToCoordinatesAsync(self, ra_hours, dec_deg):
        c = self.client
        if c.has(self.device, "ON_COORD_SET"):
            c.switch(self.device, "ON_COORD_SET", "TRACK")
        c.new(self.device, "EQUATORIAL_EOD_COORD", {"RA": ra_hours, "DEC": dec_deg})

    @property
    def Slewing(self):
        return self.client.get(self.device, "EQUATORIAL_EOD_COORD")["state"] == "Busy"

    def AbortSlew(self):
        self.client.switch(self.device, "TELESCOPE_ABORT_MOTION", "ABORT")

    @property
    def AtPark(self):
        if not self.client.has(self.device, "TELESCOPE_PARK"):
            return False
        return self._value("TELESCOPE_PARK", "PARK") == "On"

    def Park(self):
        self.client.switch(self.device, "TELESCOPE_PARK", "PARK")

    def Unpark(self):
        self.client.switch(self.device, "TELESCOPE_PARK", "UNPARK")
        self.client.wait_state(self.device, "TELESCOPE_PARK", timeout=60)

    @property
    def Tracking(self):
        if not self.client.has(self.device, "TELESCOPE_TRACK_STATE"):
            return not self.AtPark
        return self._value("TELESCOPE_TRACK_STATE", "TRACK_ON") == "On"

    @Tracking.setter
    def Tracking(self, value):
        if self.client.has(self.device, "TELESCOPE_TRACK_STATE"):  # otherwise ON_COORD_SET=TRACK tracks
            self.client.switch(self.device, "TELESCOPE_TRACK_STATE", "TRACK_ON" if value else "TRACK_OFF")

    @property
    def SideOfPier(self):
        if not self.client.has(self.device, "TELESCOPE_PIER_SIDE"):
            raise IndiError("pier side not reported")
        return 0 if self._value("TELESCOPE_PIER_SIDE", "PIER_EAST") == "On" else 1


class IndiCamera(_Device):
    def __init__(self, client, device):
        super().__init__(client, device)
        client.enable_blobs(device)
        self._started = None

    def StartExposure(self, duration, light=True):
        c = self.client
        if c.has(self.device, "CCD_FRAME_TYPE"):
            c.switch(
                self.device,
                "CCD_FRAME_TYPE",
                "FRAME_LIGHT" if light else ("FRAME_BIAS" if duration == 0 else "FRAME_DARK"),
            )
        self._started = time.monotonic()
        c.new(self.device, "CCD_EXPOSURE", {"CCD_EXPOSURE_VALUE": duration})

    @property
    def ImageReady(self):
        blob = self.client.blobs.get((self.device, "CCD1"))
        return bool(self._started is not None and blob and blob[0] >= self._started)

    @property
    def ImageArray(self):
        from astropy.io import fits

        _, data, _ = self.client.blobs[(self.device, "CCD1")]
        with fits.open(io.BytesIO(data)) as hdul:
            return np.asarray(hdul[0].data).T  # ASCOM orientation [x][y], like Alpaca

    def AbortExposure(self):
        self.client.switch(self.device, "CCD_ABORT_EXPOSURE", "ABORT")

    @property
    def CCDTemperature(self):
        return self._value("CCD_TEMPERATURE", "CCD_TEMPERATURE_VALUE")

    @property
    def SetCCDTemperature(self):
        return self._optional("CCD_TEMPERATURE", "CCD_TEMPERATURE_VALUE")

    @SetCCDTemperature.setter
    def SetCCDTemperature(self, value):
        self.client.new(self.device, "CCD_TEMPERATURE", {"CCD_TEMPERATURE_VALUE": value})

    @property
    def CoolerOn(self):
        return self._optional("CCD_COOLER", "COOLER_ON") == "On"

    @CoolerOn.setter
    def CoolerOn(self, on):
        if self.client.has(self.device, "CCD_COOLER"):  # many drivers switch the cooler with the set point
            self.client.switch(self.device, "CCD_COOLER", "COOLER_ON" if on else "COOLER_OFF")

    @property
    def CoolerPower(self):
        return self._optional("CCD_COOLER_POWER", "CCD_COOLER_VALUE")

    @property
    def BinX(self):
        return int(self._value("CCD_BINNING", "HOR_BIN"))

    @BinX.setter
    def BinX(self, v):
        if not self.client.has(self.device, "CCD_BINNING"):
            if int(v) == 1:
                return  # cameras without binning control are always 1x1
            raise IndiError(f"{self.device} cannot bin")
        self.client.new(self.device, "CCD_BINNING", {"HOR_BIN": v, "VER_BIN": v})

    BinY = BinX


class IndiFilterWheel(_Device):
    @property
    def Names(self):
        values = self.client.get(self.device, "FILTER_NAME")["values"]
        return [values[k] for k in sorted(values, key=lambda k: int("".join(ch for ch in k if ch.isdigit()) or 0))]

    @property
    def Position(self):
        prop = self.client.get(self.device, "FILTER_SLOT")
        return -1 if prop["state"] == "Busy" else int(prop["values"]["FILTER_SLOT_VALUE"]) - 1

    @Position.setter
    def Position(self, index):
        self.client.new(self.device, "FILTER_SLOT", {"FILTER_SLOT_VALUE": index + 1})


class IndiFocuser(_Device):
    @property
    def Position(self):
        return int(self._value("ABS_FOCUS_POSITION", "FOCUS_ABSOLUTE_POSITION"))

    def Move(self, position):
        self.client.new(self.device, "ABS_FOCUS_POSITION", {"FOCUS_ABSOLUTE_POSITION": position})

    @property
    def IsMoving(self):
        return self.client.get(self.device, "ABS_FOCUS_POSITION")["state"] == "Busy"

    @property
    def Temperature(self):
        return self._optional("FOCUS_TEMPERATURE", "TEMPERATURE")


class IndiDome(_Device):
    def CloseShutter(self):
        self.client.switch(self.device, "DOME_SHUTTER", "SHUTTER_CLOSE")

    def Park(self):
        if self.client.has(self.device, "DOME_PARK"):
            self.client.switch(self.device, "DOME_PARK", "PARK")


class IndiWeather(_Device):
    @property
    def IsSafe(self):
        """Safe only when the driver's overall weather status light is Ok."""
        return self.client.get(self.device, "WEATHER_STATUS")["state"] == "Ok"


ADAPTERS = {
    "mount": IndiTelescope,
    "camera": IndiCamera,
    "filterwheel": IndiFilterWheel,
    "focuser": IndiFocuser,
    "dome": IndiDome,
    "monitor": IndiWeather,
}
