"""A small INDI server speaking the XML protocol: telescope, CCD and weather simulators."""

import base64
import io
import socket
import threading
import time
import xml.etree.ElementTree as ET

import numpy as np
from astropy.io import fits

TEL, CCD, WX = "Telescope Simulator", "CCD Simulator", "Weather Simulator"


class FakeIndiServer:
    def __init__(self, slew_time=0.3):
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(4)
        self.port = self.sock.getsockname()[1]
        self.slew_time = slew_time
        self.state = {"ra": 0.0, "dec": 90.0, "parked": True, "weather_ok": True, "connected": set()}
        self.received = []
        threading.Thread(target=self._accept, daemon=True).start()

    def _accept(self):
        while True:
            conn, _ = self.sock.accept()
            threading.Thread(target=self._serve, args=(conn,), daemon=True).start()

    def _send(self, conn, xml):
        conn.sendall(xml.encode())

    def _defs(self, conn):
        for dev in (TEL, CCD, WX):
            self._send(
                conn,
                f'<defSwitchVector device="{dev}" name="CONNECTION" state="Idle" perm="rw" rule="OneOfMany">'
                '<defSwitch name="CONNECT">Off</defSwitch><defSwitch name="DISCONNECT">On</defSwitch></defSwitchVector>',
            )
        s = self.state
        self._send(
            conn,
            f'<defNumberVector device="{TEL}" name="EQUATORIAL_EOD_COORD" state="Ok" perm="rw">'
            f'<defNumber name="RA" format="%010.6m">{s["ra"]}</defNumber><defNumber name="DEC">{s["dec"]}</defNumber>'
            "</defNumberVector>",
        )
        self._send(
            conn,
            f'<defSwitchVector device="{TEL}" name="ON_COORD_SET" state="Ok" perm="rw" rule="OneOfMany">'
            '<defSwitch name="TRACK">On</defSwitch><defSwitch name="SLEW">Off</defSwitch></defSwitchVector>',
        )
        self._send(conn, self._park_xml("def"))
        self._send(
            conn,
            f'<defSwitchVector device="{TEL}" name="TELESCOPE_ABORT_MOTION" state="Idle" perm="rw" rule="AtMostOne">'
            '<defSwitch name="ABORT">Off</defSwitch></defSwitchVector>',
        )
        self._send(
            conn,
            f'<defNumberVector device="{CCD}" name="CCD_EXPOSURE" state="Idle" perm="rw">'
            '<defNumber name="CCD_EXPOSURE_VALUE">0</defNumber></defNumberVector>',
        )
        self._send(
            conn,
            f'<defNumberVector device="{CCD}" name="CCD_TEMPERATURE" state="Ok" perm="rw">'
            '<defNumber name="CCD_TEMPERATURE_VALUE">-10.0</defNumber></defNumberVector>',
        )
        self._send(
            conn,
            f'<defBLOBVector device="{CCD}" name="CCD1" state="Idle" perm="ro"><defBLOB name="CCD1"/></defBLOBVector>',
        )
        self._send(conn, self._weather_xml("def"))

    def _park_xml(self, verb):
        p = self.state["parked"]
        return (
            f'<{verb}SwitchVector device="{TEL}" name="TELESCOPE_PARK" state="Ok" perm="rw" rule="OneOfMany">'
            f'<{verb[:3] if verb == "def" else "one"}Switch name="PARK">{"On" if p else "Off"}</{verb[:3] if verb == "def" else "one"}Switch>'
            f'<{verb[:3] if verb == "def" else "one"}Switch name="UNPARK">{"Off" if p else "On"}</{verb[:3] if verb == "def" else "one"}Switch>'
            f"</{verb}SwitchVector>"
        )

    def _weather_xml(self, verb):
        ok = "Ok" if self.state["weather_ok"] else "Alert"
        el = "defLight" if verb == "def" else "oneLight"
        return (
            f'<{verb}LightVector device="{WX}" name="WEATHER_STATUS" state="{ok}">'
            f'<{el} name="WEATHER_RAIN_HOUR">{ok}</{el}></{verb}LightVector>'
        )

    def _serve(self, conn):
        parser = ET.XMLPullParser(events=("end",))
        parser.feed(b"<stream>")
        while True:
            data = conn.recv(65536)
            if not data:
                return
            parser.feed(data)
            for _, el in parser.read_events():
                if el.tag == "getProperties":
                    self._defs(conn)
                elif el.tag.startswith("new"):
                    self.received.append((el.get("device"), el.get("name"), {c.get("name"): c.text for c in el}))
                    self._handle(conn, el)

    def _handle(self, conn, el):
        dev, name = el.get("device"), el.get("name")
        vals = {c.get("name"): (c.text or "").strip() for c in el}
        if name == "CONNECTION":
            self._send(
                conn,
                f'<setSwitchVector device="{dev}" name="CONNECTION" state="Ok">'
                f'<oneSwitch name="CONNECT">On</oneSwitch><oneSwitch name="DISCONNECT">Off</oneSwitch></setSwitchVector>',
            )
        elif name == "TELESCOPE_PARK":
            self.state["parked"] = vals.get("PARK") == "On"
            self._send(conn, self._park_xml("set"))
        elif name == "EQUATORIAL_EOD_COORD":
            self._send(
                conn,
                f'<setNumberVector device="{TEL}" name="EQUATORIAL_EOD_COORD" state="Busy">'
                f'<oneNumber name="RA">{self.state["ra"]}</oneNumber><oneNumber name="DEC">{self.state["dec"]}</oneNumber></setNumberVector>',
            )
            time.sleep(self.slew_time)
            self.state["ra"], self.state["dec"] = float(vals["RA"]), float(vals["DEC"])
            self._send(
                conn,
                f'<setNumberVector device="{TEL}" name="EQUATORIAL_EOD_COORD" state="Ok">'
                f'<oneNumber name="RA">{self.state["ra"]}</oneNumber><oneNumber name="DEC">{self.state["dec"]}</oneNumber></setNumberVector>',
            )
        elif name == "CCD_EXPOSURE":
            buf = io.BytesIO()
            fits.PrimaryHDU(np.full((30, 40), 1000, np.int16)).writeto(buf)
            b64 = base64.b64encode(buf.getvalue()).decode()
            self._send(
                conn,
                f'<setBLOBVector device="{CCD}" name="CCD1" state="Ok"><oneBLOB name="CCD1" size="{len(buf.getvalue())}" '
                f'format=".fits">{b64}</oneBLOB></setBLOBVector>',
            )

    def set_weather(self, ok, conn_sender):
        self.state["weather_ok"] = ok
        conn_sender(self._weather_xml("set"))
