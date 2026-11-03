"""PHD2 guiding through its event server (JSON-RPC, one JSON object per line, TCP port 4400).

Methods used: guide (start guiding and wait for SettleDone), dither (move the lock position
and wait for SettleDone), stop_capture, get_app_state. Settling uses PHD2's own criterion:
within `pixels` for `time` seconds, failing after `timeout` seconds.
"""

import json
import socket
import time


class GuiderError(RuntimeError):
    pass


class PHD2:
    def __init__(self, host="127.0.0.1", port=4400, settle_pixels=1.5, settle_time=10, settle_timeout=60):
        self.addr = (host, port)
        self.settle = {"pixels": settle_pixels, "time": settle_time, "timeout": settle_timeout}
        self._sock = None
        self._buf = b""
        self._id = 0

    def connect(self, timeout=10):
        self._sock = socket.create_connection(self.addr, timeout=timeout)

    def close(self):
        if self._sock:
            self._sock.close()
            self._sock = None
        self._buf = b""

    def _lines(self, deadline):
        while True:
            while b"\n" in self._buf:
                line, self._buf = self._buf.split(b"\n", 1)
                if line.strip():
                    yield json.loads(line)
            self._sock.settimeout(max(0.1, deadline - time.monotonic()))
            try:
                chunk = self._sock.recv(65536)
            except TimeoutError:
                raise GuiderError("PHD2 did not answer in time") from None
            except OSError as e:
                self.close()  # reset by PHD2: the next call connects again
                raise GuiderError(f"PHD2 connection lost: {e}") from None
            if not chunk:
                self.close()  # PHD2 was closed or restarted: the next call connects again
                raise GuiderError("PHD2 closed the connection")
            self._buf += chunk

    def call(self, method, params=None, timeout=30):
        if self._sock is None:
            self.connect()
        self._id += 1
        msg = {"method": method, "id": self._id}
        if params is not None:
            msg["params"] = params
        try:
            self._sock.sendall((json.dumps(msg) + "\r\n").encode())
        except OSError:
            self.close()  # the link dropped: the next call connects again
            raise
        for obj in self._lines(time.monotonic() + timeout):
            if obj.get("id") == self._id:
                if "error" in obj:
                    raise GuiderError(f"PHD2 {method}: {obj['error'].get('message', obj['error'])}")
                return obj.get("result")

    def _wait_settled(self):
        deadline = time.monotonic() + self.settle["timeout"] + 30
        for obj in self._lines(deadline):
            if obj.get("Event") == "SettleDone":
                if obj.get("Status", 0) != 0:
                    raise GuiderError(f"guiding did not settle: {obj.get('Error', 'unknown error')}")
                return

    def guide(self, recalibrate=False):
        self.call("guide", {"settle": self.settle, "recalibrate": recalibrate})
        self._wait_settled()

    def dither(self, amount=3.0, ra_only=False):
        self.call("dither", {"amount": amount, "raOnly": ra_only, "settle": self.settle})
        self._wait_settled()

    def stop(self):
        self.call("stop_capture")

    def state(self):
        return self.call("get_app_state")
