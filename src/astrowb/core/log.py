"""The program's log (plans/architecture.md ARC-17): app.log beside the settings, kept to three files of 1 MB, one
line per record (time, level, where, message). Every module's logging.getLogger(__name__) writes into it; the
problem report sends its last lines.

    log.start(settings.path.parent)     # once, at start-up
    log.tail(folder, 500)               # the newest lines
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

NAME = "app.log"
FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def start(folder, level=logging.INFO):
    """Log to folder/app.log (rotating). A folder that cannot be written leaves logging as it was."""
    root = logging.getLogger()
    if any(getattr(h, "_astrowb", False) for h in root.handlers):
        return None
    try:
        handler = RotatingFileHandler(Path(folder) / NAME, maxBytes=1_000_000, backupCount=2, encoding="utf-8")
    except OSError:
        return None
    handler._astrowb = True
    handler.setFormatter(logging.Formatter(FORMAT, "%Y-%m-%d %H:%M:%S"))
    root.addHandler(handler)
    root.setLevel(level)
    return handler


def tail(folder, lines=500):
    """The newest lines of app.log (the rotated files are older), or ""."""
    path = Path(folder) / NAME
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(text[-lines:]) + "\n"
