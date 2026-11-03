"""What the UI uses to talk to the observatory process. Standard library only, so the window starts fast.

http://… on the local computer or a trusted network; https://… with the certificate fingerprint the
observatory shows (see devices/tls.py) anywhere else.
"""

import hashlib
import http.client
import json
import re
import shutil
import ssl
import urllib.parse
from pathlib import Path


class Client:
    def __init__(self, url, token, timeout=10, fingerprint=None):
        self.url, self.token, self.timeout = url.rstrip("/"), token, timeout
        self.fingerprint = (fingerprint or "").replace(":", "").strip().lower() or None
        parts = urllib.parse.urlsplit(self.url)
        self._https, self._host, self._port = parts.scheme == "https", parts.hostname, parts.port

    def _open(self, method, path, body=None, timeout=None):
        """The response of one request (caller reads it); errors as RuntimeError with the server's message."""
        timeout = timeout or self.timeout
        if self._https:
            if not self.fingerprint:
                raise RuntimeError("https needs the observatory's certificate fingerprint")
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE  # pinned below instead
            conn = http.client.HTTPSConnection(self._host, self._port or 443, timeout=timeout, context=ctx)
            conn.connect()
            seen = hashlib.sha256(conn.sock.getpeercert(binary_form=True)).hexdigest()
            if seen != self.fingerprint:  # checked before the token is sent
                conn.close()
                raise RuntimeError(f"the observatory's certificate does not match (it shows {seen[:16]}…)")
        else:
            conn = http.client.HTTPConnection(self._host, self._port or 80, timeout=timeout)
        data = None if body is None else json.dumps(body).encode()
        conn.request(method, path, data, {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"})
        r = conn.getresponse()
        if r.status >= 400:
            text = r.read()
            conn.close()
            try:
                message = json.loads(text or b"{}").get("error")
            except ValueError:
                message = None
            raise RuntimeError(message or f"HTTP {r.status} {r.reason}")
        return r

    def _request(self, method, path, body=None):
        r = self._open(method, path, body)
        try:
            return json.loads(r.read())
        finally:
            r.close()

    def status(self):
        return self._request("GET", "/status")

    def post(self, path, body=None):
        return self._request("POST", path, body or {})

    def download(self, path, folder) -> Path:
        """Copy a frame the observatory saved into a local folder; a broken transfer leaves no file."""
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / re.split(r"[\\/]", str(path))[-1]  # the observatory may run on Windows
        part = target.with_name(target.name + ".part")
        try:
            r = self._open("GET", "/file?" + urllib.parse.urlencode({"path": str(path)}), timeout=max(self.timeout, 60))
            with r, open(part, "wb") as f:
                shutil.copyfileobj(r, f)
        except BaseException:
            part.unlink(missing_ok=True)
            raise
        part.replace(target)
        return target
