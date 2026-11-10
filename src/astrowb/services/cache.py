"""Answers of catalogues and archives kept on disk, so that a second look-up is instant and work goes on offline
(ARC-14 items 1 and 2).

    rows = cached("vizier", ("I/355/gaiadr3", ra, dec, radius), lambda: query(...))

The request (any JSON-able value) names the answer; AGES says how long an answer stays fresh for each service
(catalogues forever, ephemerides a week, light-curve archives a day). When the network fails, an older answer is
used; when the user works offline (ASTROWB_OFFLINE=1, the setting services.offline), only the cache answers and a
missing answer raises OfflineError. The cache keeps at most MAX_BYTES, dropping the oldest answers first.
"""

import hashlib
import json
import os
import pickle
import sqlite3
import time
from contextlib import closing

ENV = "ASTROWB_OFFLINE"
MAX_BYTES = 2 << 30
DAY = 86400.0
AGES = {"ephemerides": 7 * DAY, "lightcurves": DAY, "updates": DAY}  # services not listed: answers never age
last = {}  # service -> (fetched time, from the cache?) of the latest answer: windows say "from cache, fetched on …"


class OfflineError(ConnectionError):
    pass


def offline():
    return os.environ.get(ENV, "") not in ("", "0")


def set_offline(on):
    """For this process and the worker processes it starts."""
    os.environ[ENV] = "1" if on else "0"


def folder():
    from ..settings import config_dir

    return config_dir() / "cache"


def _db():
    folder().mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(folder() / "index.sqlite", timeout=30)  # worker processes write at the same time
    db.execute(
        "CREATE TABLE IF NOT EXISTS answers (service TEXT, key TEXT, file TEXT, fetched REAL, size INTEGER,"
        " request TEXT, PRIMARY KEY (service, key))"
    )
    return db


def _key(service, request):
    text = json.dumps(request, sort_keys=True, default=str)
    return hashlib.blake2b(f"{service}\n{text}".encode(), digest_size=16).hexdigest(), text


def _read(service, key):
    with closing(_db()) as db, db:
        row = db.execute("SELECT file, fetched FROM answers WHERE service = ? AND key = ?", (service, key)).fetchone()
    if row is None:
        return None
    try:
        return pickle.loads((folder() / row[0]).read_bytes()), row[1]  # noqa: S301 - files this program wrote
    except (OSError, pickle.UnpicklingError, EOFError):
        return None


def _write(service, key, request, value):
    data = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
    rel = f"{service}/{key}.pkl"
    path = folder() / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_bytes(data)
    tmp.replace(path)  # a reader never sees half an answer
    with closing(_db()) as db, db:
        db.execute(
            "INSERT OR REPLACE INTO answers VALUES (?, ?, ?, ?, ?, ?)",
            (service, key, rel, time.time(), len(data), request[:2000]),
        )
        total = db.execute("SELECT COALESCE(SUM(size), 0) FROM answers").fetchone()[0]
        if total > MAX_BYTES:
            for svc, k, f, size in db.execute(
                "SELECT service, key, file, size FROM answers ORDER BY fetched"
            ).fetchall():
                if total <= MAX_BYTES * 0.8:
                    break
                (folder() / f).unlink(missing_ok=True)
                db.execute("DELETE FROM answers WHERE service = ? AND key = ?", (svc, k))
                total -= size


def cached(service, request, fetch):
    """fetch() once per request (and again when the answer has aged); errors of fetch() fall back to an older
    answer when there is one."""
    key, text = _key(service, request)
    hit = _read(service, key)
    age = AGES.get(service)
    if hit is not None and (age is None or time.time() - hit[1] < age):
        last[service] = (hit[1], True)
        return hit[0]
    if offline():
        if hit is not None:
            last[service] = (hit[1], True)
            return hit[0]
        raise OfflineError(f"working offline: the answer of {service} is not in the cache")
    try:
        value = fetch()
    except LookupError:  # the service answered "not there": that is an answer, not a network failure
        raise
    except Exception:
        if hit is None:
            raise
        last[service] = (hit[1], True)
        return hit[0]
    try:
        _write(service, key, text, value)
    except (OSError, sqlite3.Error, pickle.PicklingError):
        pass  # a full disk or a read-only folder: the answer is still given, only not kept
    last[service] = (time.time(), False)
    return value


def size():
    """(answers, bytes) in the cache."""
    try:
        with closing(_db()) as db, db:
            return db.execute("SELECT COUNT(*), COALESCE(SUM(size), 0) FROM answers").fetchone()
    except sqlite3.Error:
        return 0, 0


def clear():
    import shutil

    shutil.rmtree(folder(), ignore_errors=True)
