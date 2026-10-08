"""Project file: one SQLite database holding file references and the record of every step run.

Raw frames are referenced, not copied (they can be tens of GB). Paths inside the
project folder are stored relative so the project can be moved as a whole.
"""

import json
import os
import platform
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path

from .. import __version__

EXTENSION = ".astroproj"
SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY,
    path TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL,
    size INTEGER,
    mtime REAL,
    added TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY,
    step TEXT NOT NULL,
    params TEXT NOT NULL,
    inputs TEXT NOT NULL,
    outputs TEXT,
    status TEXT NOT NULL,
    error TEXT,
    started TEXT NOT NULL,
    finished TEXT,
    environment TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    area TEXT NOT NULL,
    name TEXT NOT NULL,
    json TEXT NOT NULL,
    saved TEXT NOT NULL,
    PRIMARY KEY (area, name)
);
"""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def environment() -> dict:
    """Software versions recorded with each run, for reproducibility."""
    import astropy
    import numpy

    return {
        "app": __version__,
        "python": platform.python_version(),
        "numpy": numpy.__version__,
        "astropy": astropy.__version__,
        "os": platform.platform(),
    }


class Project:
    def __init__(self, path: Path):
        self.path = Path(path)
        if self.path.suffix != EXTENSION:
            raise ValueError(f"project file must end with {EXTENSION}")
        self.db = sqlite3.connect(self.path, check_same_thread=False)  # runs are recorded from the task monitor thread
        self.lock = threading.RLock()
        self.db.row_factory = sqlite3.Row
        with self.lock, self.db:
            self.db.executescript(_SCHEMA)
            self.db.execute(
                "INSERT OR IGNORE INTO meta VALUES ('schema_version', ?), ('created', ?)",
                (str(SCHEMA_VERSION), _now()),
            )
        version = int(self.meta("schema_version"))
        if version > SCHEMA_VERSION:
            self.db.close()
            raise RuntimeError(f"project was written by a newer version (schema {version})")

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def meta(self, key: str) -> str | None:
        with self.lock:
            row = self.db.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None

    # --- files -------------------------------------------------------------
    def _store(self, path: Path) -> str:
        path = Path(path).resolve()
        try:
            return path.relative_to(self.path.parent.resolve()).as_posix()
        except ValueError:
            return str(path)

    def resolve(self, stored: str) -> Path:
        p = Path(stored)
        return p if p.is_absolute() else self.path.parent / p

    def add_file(self, path: Path, kind: str) -> int:
        st = os.stat(path)
        with self.lock, self.db:
            self.db.execute(
                "INSERT INTO files (path, kind, size, mtime, added) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(path) DO UPDATE SET kind = excluded.kind, size = excluded.size, mtime = excluded.mtime",
                (self._store(path), kind, st.st_size, st.st_mtime, _now()),
            )
            return self.db.execute("SELECT id FROM files WHERE path = ?", (self._store(path),)).fetchone()[0]

    def files(self, kind: str | None = None) -> list[dict]:
        sql, args = "SELECT * FROM files", ()
        if kind:
            sql, args = sql + " WHERE kind = ?", (kind,)
        with self.lock:
            rows = self.db.execute(sql + " ORDER BY id", args).fetchall()
        return [dict(r) | {"path": str(self.resolve(r["path"]))} for r in rows]

    # --- runs --------------------------------------------------------------
    def start_run(self, step: str, inputs: dict, params: dict) -> int:
        with self.lock, self.db:
            cur = self.db.execute(
                "INSERT INTO runs (step, params, inputs, status, started, environment) "
                "VALUES (?, ?, ?, 'running', ?, ?)",
                (step, json.dumps(params), json.dumps(inputs), _now(), json.dumps(environment())),
            )
        return cur.lastrowid

    def finish_run(self, run_id: int, status: str, outputs: dict | None = None, error: str | None = None):
        with self.lock, self.db:
            self.db.execute(
                "UPDATE runs SET status = ?, outputs = ?, error = ?, finished = ? WHERE id = ?",
                (status, json.dumps(outputs) if outputs is not None else None, error, _now(), run_id),
            )

    def runs(self, step: str | None = None, full: bool = True) -> list[dict]:
        """Every run in order; full=False leaves out inputs, outputs and environment (fast for long histories)."""
        cols = "*" if full else "id, step, status, started, finished, params, error"
        sql, args = f"SELECT {cols} FROM runs", ()
        if step:
            sql, args = sql + " WHERE step = ?", (step,)
        with self.lock:
            rows = self.db.execute(sql + " ORDER BY id", args).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            for k in ("params", "inputs", "outputs", "environment"):
                if k in d:
                    d[k] = json.loads(d[k]) if d[k] is not None else None
            out.append(d)
        return out

    def run(self, run_id: int) -> dict:
        """One run with everything recorded about it."""
        with self.lock:
            row = self.db.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(run_id)
        d = dict(row)
        for k in ("params", "inputs", "outputs", "environment"):
            d[k] = json.loads(d[k]) if d[k] is not None else None
        return d

    # --- sessions (the state of an area window, core/state.py) -------------------
    def save_session(self, area: str, text: str, name: str = "last"):
        with self.lock, self.db:
            self.db.execute("INSERT OR REPLACE INTO sessions VALUES (?, ?, ?, ?)", (area, name, text, _now()))

    def session(self, area: str, name: str = "last") -> str | None:
        """The saved JSON of an area's session, or None."""
        with self.lock:
            row = self.db.execute("SELECT json FROM sessions WHERE area = ? AND name = ?", (area, name)).fetchone()
        return row[0] if row else None
