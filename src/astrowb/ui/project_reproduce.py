"""Project page "Reproduce…": run a step again, keep a copy of the old products and compare (ARC-11.5)."""

import json
import time
from pathlib import Path

from PySide6.QtCore import QCoreApplication

from ..core import reproduce
from . import messages

translate = QCoreApplication.translate


def rerun_run(window, run_id):
    """The same step with the recorded inputs and settings, recorded as a new run."""
    run = window.engine.project.run(run_id)
    return window.run_step(
        run["step"],
        run["inputs"],
        run["params"],
        on_done=lambda out: window.project_page.details.setPlainText(json.dumps(out, indent=1, default=str)[:20000]),
    )


def reproduce_run(window, run_id):
    """Only this run is redone, not the chain of runs before it."""
    run = window.engine.project.run(run_id)
    folder = Path(window.engine.project.path).parent / "reproduce" / f"run-{run_id}-{time.strftime('%Y%m%d-%H%M%S')}"
    try:
        before = reproduce.snapshot(run["outputs"], folder)
    except OSError as e:
        return messages.save_failed(window, e)

    def done(out):
        lines = reproduce.report(before, out, run["outputs"]) or [translate("Reproduce", "No products to compare.")]
        text = "\n".join(lines)
        try:
            (folder / "report.txt").write_text(text + "\n", encoding="utf-8")
        except OSError as e:
            messages.save_failed(window, e)
        window.project_page.details.setPlainText(
            translate("Reproduce", "Copies of the old products and the report: {folder}").format(folder=folder)
            + "\n\n"
            + text
            + "\n\n"
            + json.dumps(out, indent=1, default=str)[:20000]
        )

    return window.run_step(run["step"], run["inputs"], run["params"], on_done=done)
