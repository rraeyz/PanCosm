import os

import numpy as np
import pytest
from astropy.io import fits

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def pytest_sessionstart(session):
    """Compiled translations (*.qm) are not kept in git: build them when missing or older than their .ts, so a fresh
    clone passes without remembering `python tools/i18n.py` (plans/architecture.md ARC-2)."""
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    i18n = root / "src" / "astrowb" / "resources" / "i18n"
    stale = [
        ts
        for ts in i18n.glob("app_*.ts")
        if not ts.with_suffix(".qm").exists() or ts.with_suffix(".qm").stat().st_mtime < ts.stat().st_mtime
    ]
    if stale:
        subprocess.run([sys.executable, str(root / "tools" / "i18n.py")], check=True, capture_output=True)


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    monkeypatch.setenv("ASTROWB_CONFIG_DIR", str(tmp_path / "config"))


@pytest.fixture
def fits_file(tmp_path):
    rng = np.random.default_rng(1)
    data = rng.normal(1000, 10, (64, 80)).astype(np.float32)
    data[30:34, 40:44] += 5000  # a "star"
    hdr = fits.Header({"OBJECT": "TEST", "EXPTIME": 30.0})
    path = tmp_path / "frame.fits"
    fits.PrimaryHDU(data, hdr).writeto(path)
    return path


def pytest_unconfigure(config):
    """What still runs when the tests are over, and a bounded wait for it: on macOS CI (2026-11-09) every test passed
    and the run then hung for 34 minutes with two Python processes left; now it says what is left, and two minutes
    later prints every thread's stack and ends."""
    import faulthandler
    import multiprocessing as mp
    import sys
    import threading

    threads = [
        t.name for t in threading.enumerate() if t.is_alive() and not t.daemon and t is not threading.main_thread()
    ]
    children = [f"{p.name} ({p.pid})" for p in mp.active_children()]
    if threads or children:
        print(f"\nstill running after the tests: threads {threads}, processes {children}", file=sys.stderr)
    faulthandler.dump_traceback_later(120, exit=True)
