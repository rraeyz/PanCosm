"""Automation window: the run plan shown before Run (plans/automation.md AUT-2.3, UI-16.12)."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QPlainTextEdit, QVBoxLayout

from ..engine import automation, steps
from .automation_run import missing_by_step
from .names import step_name

translate = QCoreApplication.translate
SKIP_KEY = "dialog.automation_run_plan_skip"  # in INTERNAL ("dialog.")


def plan_text(auto, inputs):
    """Per step in order: its inputs with where each comes from, and what is missing. Nothing is said about reuse:
    the engine has no incremental runs yet, so every step runs."""
    own = automation.defaults(auto)
    made, lines = {}, []
    missing = missing_by_step(auto, set(own) | set(inputs))
    for n, entry in enumerate(auto["steps"], 1):
        s = steps.get(entry["step"])
        lines.append(f"{n}. {step_name(entry['step'])}")
        links = entry.get("inputs", {})
        for name in s.inputs:
            for key in automation._keys(links.get(name, name)):
                if key in made:
                    src = translate("AutomationPlan", "output of step {n}").format(n=made[key])
                elif key in inputs:
                    src = translate("AutomationPlan", "asked in the form")
                elif key in own:
                    src = translate("AutomationPlan", "the automation's value")
                else:
                    src = translate("AutomationPlan", "missing")
                lines.append(f"     {key} ← {src}")
        if missing[n - 1]:
            lines.append("     " + translate("AutomationPlan", "needs {names}").format(names=", ".join(missing[n - 1])))
        made.update({k: n for k in s.outputs})
    return "\n".join(lines)


def confirm_plan(page, auto, inputs):
    """True when the run may go on. Only a page inside a window with a results area shows the plan (as the "Run
    plan" tab, made at first use, and a dialog with "Don't ask again")."""
    win = page.window()
    if not hasattr(win, "add_result_tab"):
        return True
    text = plan_text(auto, inputs)
    view = getattr(page, "_plan_view", None)
    if view is None:
        view = page._plan_view = QPlainTextEdit(win)
        view.setReadOnly(True)
        win.add_result_tab("run_plan", translate("AutomationPlan", "Run plan"), view)
    view.setPlainText(text)
    if win.settings.get(SKIP_KEY) or page.__dict__.pop("unattended", False):
        return True
    dlg = QDialog(win)
    dlg.setWindowTitle(translate("AutomationPlan", "Run plan"))
    box, again = QVBoxLayout(dlg), QCheckBox(translate("AutomationPlan", "Don't ask again"), dlg)
    shown = QPlainTextEdit(text, dlg)
    shown.setReadOnly(True)
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dlg)
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    for w in (shown, again, buttons):
        box.addWidget(w)
    ok = dlg.exec() == QDialog.Accepted
    if ok and again.isChecked():
        win.settings.set(SKIP_KEY, True)
    return ok
