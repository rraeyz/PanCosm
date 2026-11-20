"""The one HTTP GET of the services (plans/architecture.md ARC-14); callers decode and cache the bytes."""

import urllib.parse
import urllib.request


def get(url, params=None, timeout=60, agent=None):
    """The body (bytes) of url (+ urlencoded params); agent is the User-Agent header, none: Python's own."""
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    headers = {"User-Agent": agent} if agent else {}
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as r:  # noqa: S310 (fixed https services)
        return r.read()
