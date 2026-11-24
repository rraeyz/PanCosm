"""The HTTP GET and form POST of the services (plans/architecture.md ARC-14); callers decode and cache the bytes."""

import urllib.error
import urllib.parse
import urllib.request

HTTPError = urllib.error.HTTPError


def url_of(url, params=None):
    """url (+ urlencoded params)."""
    return url + "?" + urllib.parse.urlencode(params) if params else url


def _open(url, params, timeout, agent, headers, method, context, data=None):
    head = dict(headers or {})
    if agent:
        head["User-Agent"] = agent
    req = urllib.request.Request(url_of(url, params), data=data, headers=head, method=method)
    kw = {"context": context} if context else {}
    return urllib.request.urlopen(req, timeout=timeout, **kw)  # noqa: S310 (fixed https services)


def get(url, params=None, timeout=60, agent=None, headers=None, context=None):
    """The body (bytes) of url (+ urlencoded params); agent is the User-Agent header, none: Python's own;
    headers: more request headers; context: an ssl context."""
    with _open(url, params, timeout, agent, headers, "GET", context) as r:
        return r.read()


def post(url, form, timeout=60):
    """The body (bytes) of the answer to a form POST of the dict form; a redirect is followed (as a GET)."""
    with _open(url, None, timeout, None, None, "POST", None, urllib.parse.urlencode(form).encode()) as r:
        return r.read()


def head_status(url, timeout=30, agent=None):
    """The HTTP status of a HEAD request to url (errors raise as urlopen does)."""
    with _open(url, None, timeout, agent, None, "HEAD", None) as r:
        return r.status
