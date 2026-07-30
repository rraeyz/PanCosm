import json
import socket
import threading

import pytest

from astrowb.devices.phd2 import PHD2, GuiderError


class FakePHD2:
    """Answers like PHD2's event server; settles successfully unless told otherwise."""

    def __init__(self, settle_status=0):
        self.server = socket.socket()
        self.server.bind(("127.0.0.1", 0))
        self.server.listen(1)
        self.port = self.server.getsockname()[1]
        self.settle_status = settle_status
        self.received = []
        threading.Thread(target=self.serve, daemon=True).start()

    def serve(self):
        conn, _ = self.server.accept()
        conn.sendall(b'{"Event":"Version","PHDVersion":"2.6.13"}\r\n')
        buf = b""
        while True:
            data = conn.recv(4096)
            if not data:
                return
            buf += data
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                msg = json.loads(line)
                self.received.append(msg)
                if msg["method"] == "get_app_state":
                    out = [{"jsonrpc": "2.0", "result": "Guiding", "id": msg["id"]}]
                elif msg["method"] == "bogus":
                    out = [{"jsonrpc": "2.0", "error": {"code": 1, "message": "unknown method"}, "id": msg["id"]}]
                else:
                    out = [{"Event": "GuideStep", "Frame": 1}, {"jsonrpc": "2.0", "result": 0, "id": msg["id"]}]
                    if msg["method"] in ("guide", "dither"):
                        out.append({"Event": "SettleDone", "Status": self.settle_status, "Error": "lost star"})
                conn.sendall(b"".join((json.dumps(o) + "\r\n").encode() for o in out))


def test_guide_dither_state():
    fake = FakePHD2()
    g = PHD2(port=fake.port, settle_pixels=1.0)
    g.guide()
    g.dither(5.0)
    assert g.state() == "Guiding"
    methods = [m["method"] for m in fake.received]
    assert methods == ["guide", "dither", "get_app_state"]
    assert fake.received[1]["params"]["amount"] == 5.0 and fake.received[0]["params"]["settle"]["pixels"] == 1.0
    with pytest.raises(GuiderError, match="unknown method"):
        g.call("bogus")
    g.close()


def test_settle_failure_is_reported():
    g = PHD2(port=FakePHD2(settle_status=1).port)
    with pytest.raises(GuiderError, match="lost star"):
        g.guide()


def test_reconnects_after_phd2_restarts():
    """PHD2 closed (or restarted) during the night: the call fails once, the next one connects again."""
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(2)
    port = server.getsockname()[1]

    def serve():
        first, _ = server.accept()
        first.recv(4096)
        first.close()  # PHD2 goes away in the middle of a call
        conn, _ = server.accept()
        msg = json.loads(conn.recv(4096).split(b"\n")[0])
        conn.sendall((json.dumps({"jsonrpc": "2.0", "result": "Guiding", "id": msg["id"]}) + "\r\n").encode())
        conn.recv(4096)
        conn.close()

    threading.Thread(target=serve, daemon=True).start()
    g = PHD2(port=port)
    with pytest.raises(GuiderError, match="closed the connection"):
        g.state()
    assert g.state() == "Guiding"
    g.close()
    server.close()
