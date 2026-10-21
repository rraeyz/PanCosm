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


PERSONAL = ("name", "observers", "aavso_code", "mpc_code")  # the profile's names and codes


def _anonymous(values):
    """The settings without the observer's names and codes and with the site to 0.1° (about 10 km): enough to
    reproduce a time or altitude problem, not to find the observer (ARC-17)."""
    values = json.loads(json.dumps(values, default=str))
    profile = values.get("profile") or {}
    for part in ("observer", "site"):
        for key in PERSONAL:
            if key in (profile.get(part) or {}):
                profile[part][key] = "(removed)"
    for site in (profile.get("site"), values.get("site")):
        for key in ("lat", "lon"):
            if isinstance(site, dict) and isinstance(site.get(key), int | float):
                site[key] = round(site[key], 1)
    if isinstance(values.get("site"), dict) and "name" in values["site"]:
        values["site"]["name"] = "(removed)"
    values.pop("mpc", None)  # the older place of the MPC code and observers
    return values


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
    from .. import native

    lines.append(native.describe())
    try:
        lines.append(f"compute {compute.describe()}")
    except Exception as e:  # the report must be made even when the GPU check itself fails
        lines.append(f"compute check failed: {e}")
    return "\n".join(lines) + "\n"


def make_report(settings, out_path, runs=None, session=None):
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
        z.writestr("settings.json", json.dumps(_scrub(_anonymous(settings.values)), indent=1, default=str))
        from ..core import log

        z.writestr("app.log", _home(log.tail(settings.path.parent)))
        keep = ("step", "params", "status", "error", "started", "finished")
        steps = [{k: _scrub(r.get(k)) for k in keep} for r in (runs or [])][-30:]
        z.writestr("last_steps.json", json.dumps(steps, indent=1, default=str))
        gpu = settings.path.parent / "gpu-report.json"  # Help → Check the GPU (ARC-10)
        if gpu.exists():
            z.writestr("gpu-report.json", _home(gpu.read_text(encoding="utf-8", errors="replace")))
        if session is not None:  # the window in front, as its Save session would keep it: enough to redo the steps
            z.writestr("session.json", json.dumps(_scrub(session), indent=1, default=str))
        z.writestr("README.txt", f"Problem report made {datetime.now().isoformat(timespec='seconds')}\n")
    return out_path


def report_dialog(parent, settings, engine=None, path=None, session=None):
    """Help → Report a problem in any window: ask where to save (unless path), make the zip, say what to send."""
    from datetime import date

    from PySide6.QtCore import QCoreApplication
    from PySide6.QtWidgets import QFileDialog, QMessageBox

    if path is None:
        path, _ = QFileDialog.getSaveFileName(
            parent,
            QCoreApplication.translate("AreaWindow", "Report a problem"),
            str(Path.home() / f"problem-report-{date.today()}.zip"),
            "Zip (*.zip)",
        )
        if not path:
            return None
    project = getattr(engine, "project", None)
    make_report(settings, path, project.runs(full=False) if project is not None else [], session)
    QMessageBox.information(
        parent,
        QCoreApplication.translate("AreaWindow", "Report a problem"),
        QCoreApplication.translate(
            "AreaWindow",
            "The report is saved:\n{path}\n\nSend this file with a few words on what you did and what went wrong. "
            "It holds no data files and no folder names.",
        ).format(path=path),
    )
    return path
