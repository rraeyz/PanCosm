"""SIMBAD and VizieR with a fallback to their mirrors.

Both live at CDS in Strasbourg; when it does not answer (down, blocked by a network), the same services run at
Harvard, and VizieR also at IDIA (Cape Town; the Harvard VizieR answers the large catalogues such as Gaia and APASS
with nothing). cds(service, query) calls query(server) for each server in turn and keeps the first that answers for
the rest of the session, and in a small file for the worker processes started later (else each would wait for
Strasbourg again). An answer such as "not found" is passed on, not retried. A server that is up but slow is left
after `patience` seconds for the next one (its answer is not waited for; the last server gets all the time it needs):
from one network CDS did not answer in 15 s while both Harvard addresses answered in 0.7 s.
"""

import json

SERVERS = {
    "simbad": ("simbad.cds.unistra.fr", "simbad.harvard.edu", "simbad.cfa.harvard.edu", "simbad.u-strasbg.fr"),
    "vizier": ("vizier.cds.unistra.fr", "vizier.idia.ac.za", "vizier.cfa.harvard.edu"),
}
_working = {}  # service -> the server that answered last


def _file():
    from .settings import config_dir

    return config_dir() / "mirrors.json"


def _remember(service, server):
    if _working.get(service) != server:
        _working[service] = server
        try:
            _file().parent.mkdir(parents=True, exist_ok=True)
            _file().write_text(json.dumps(_working), encoding="utf-8")
        except OSError:
            pass  # only a shortcut: without it the first server is tried first again


def cds(service, query, patience=15.0):
    """query(server) on the first server of service that answers within patience seconds (astroquery:
    Simbad().server = server, Vizier(vizier_server=server))."""
    if not _working:
        try:
            _working.update(json.loads(_file().read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
    first = _working.get(service, SERVERS[service][0])
    first = first if first in SERVERS[service] else SERVERS[service][0]
    servers = [first] + [s for s in SERVERS[service] if s != first]
    error = None
    for server in servers:
        try:
            out = _within(query, server, None if server == servers[-1] else patience)
        except TimeoutError as e:  # up but slow: the next server
            error = e
            continue
        except LookupError:  # the service answered: the name or region is not there
            _remember(service, server)
            raise
        except Exception as e:  # noqa: BLE001 - network, TLS, HTTP 5xx, a TAP service that stopped: next server
            error = e
            continue
        _remember(service, server)
        return out
    raise error


def _within(query, server, seconds):
    """query(server), or TimeoutError after seconds (the call is left to finish in a daemon thread)."""
    if seconds is None:
        return query(server)
    import threading

    box = {}

    def run():
        try:
            box["out"] = query(server)
        except BaseException as e:  # noqa: BLE001 - handed to the caller
            box["error"] = e

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(seconds)
    if t.is_alive():
        raise TimeoutError(f"{server} did not answer within {seconds:.0f} s")
    if "error" in box:
        raise box["error"]
    return box["out"]
