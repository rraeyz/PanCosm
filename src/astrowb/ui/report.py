"""Help → Report a problem: one zip the owner can send, so that a problem met on the owner's machine reaches the
developer with what is needed to reproduce it (PLAN.md R6). Nothing personal goes in: no data file, and every path
is cut to its file name."""

import json
import platform
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path

ERROR_LOG_LIMIT = 200_000  # the newest part of a long error.log is the useful one
_PATHLIKE = re.compile(r"([A-Za-z]:\\|/|~[/\\])")


def _home(text):
    return text.replace(str(Path.home()), "~")


def _scrub(value):
    """Paths become their file name (folder names can be personal: user names, places); the home folder in any
    other text becomes ~; the rest is kept."""
    if isinstance(value, str):
        return Path(value.replace("\\", "/")).name if _PATHLIKE.match(value) else _home(value)
    if isinstance(value, dict):
        return {k: _scrub(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_scrub(v) for v in value]
    return value


def system_text():
    from .. import __version__, compute

    lines = [
        f"application {__version__}",
        f"python {sys.version.split()[0]} ({platform.python_implementation()})",
        f"system {platform.platform()} ({platform.machine()})",
    ]
    try:
        import PySide6
        from PySide6.QtGui import QGuiApplication

        lines.append(f"qt {PySide6.__version__}")
        app = QGuiApplication.instance()
        for screen in app.screens() if app else []:
            g = screen.availableGeometry()
            lines.append(f"screen {g.width()}x{g.height()} scale {screen.devicePixelRatio():g}")
    except ImportError:
        pass
    try:
        lines.append(f"compute {compute.describe()}")
    except Exception as e:  # the report must be made even when the GPU check itself fails
        lines.append(f"compute check failed: {e}")
    return "\n".join(lines) + "\n"


def make_report(settings, out_path, runs=None):
    """Write the zip: error.log (newest part), system.txt, settings.json and last_steps.json (step, settings,
    status, error and times of the last runs, without their input files). Returns the path."""
    out_path = Path(out_path)
    log = settings.path.parent / "error.log"
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        if log.exists():
            text = log.read_bytes()[-ERROR_LOG_LIMIT:].decode("utf-8", "replace")
            z.writestr("error.log", _home(text))  # tracebacks name files under the user's home folder
        else:
            z.writestr("error.log", "")
        z.writestr("system.txt", system_text())
        z.writestr("settings.json", json.dumps(_scrub(settings.values), indent=1, default=str))
        keep = ("step", "params", "status", "error", "started", "finished")
        steps = [{k: _scrub(r.get(k)) for k in keep} for r in (runs or [])][-30:]
        z.writestr("last_steps.json", json.dumps(steps, indent=1, default=str))
        z.writestr("README.txt", f"Problem report made {datetime.now().isoformat(timespec='seconds')}\n")
    return out_path
