"""Steps describe their settings (plans/automation.md AUT-1): kind, unit, range, choices, label and help, so a run
is checked before it starts and forms, command-line help and recipes can be made from the description.

    @step("timeseries.frequencies", inputs=("time", "flux"), outputs=(...),
          params=[P("f_max", "float", 50.0, unit="c/d", min=0, label="Highest frequency", help="...")])

The old form (@step(..., f_max=50.0)) keeps working; tests/test_step_params.py lists the steps not described yet.
"""

from dataclasses import dataclass


def QT_TRANSLATE_NOOP(context, text):  # noqa: N802 (the name pyside6-lupdate looks for; no Qt in the engine)
    """Marks a label or help text for translation (context "Steps"); the interface translates it when shown."""
    return text


KINDS = ("int", "float", "bool", "text", "choice", "file", "files", "folder", "xy", "positions", "sky", "time",
         "band", "expression", "table", "object")  # fmt: skip


@dataclass(frozen=True)
class P:
    name: str
    kind: str
    default: object = None
    unit: str | None = None
    min: float | None = None
    max: float | None = None
    choices: tuple | None = None
    label: str = ""
    help: str = ""
    advanced: bool = False

    def __post_init__(self):
        if self.kind not in KINDS:
            kind = self.kind
            raise ValueError(f"unknown parameter kind {kind}")


def problem(p, value):
    """Why value does not suit the parameter (an English message the interface translates), or None. None as a
    value is always allowed: it means "the step decides" (automatic)."""
    if value is None:
        return None
    name = p.name
    if p.kind in ("int", "float"):
        if isinstance(value, bool) or not isinstance(value, int | float):
            return f"{name} must be a number, not {value}"
        if p.kind == "int" and int(value) != value:
            return f"{name} must be a whole number, not {value}"
        if p.min is not None and value < p.min:
            low = p.min
            return f"{name} = {value} is below the smallest allowed value {low}"
        if p.max is not None and value > p.max:
            high = p.max
            return f"{name} = {value} is above the largest allowed value {high}"
    if p.kind == "bool" and not isinstance(value, bool):
        return f"{name} must be true or false, not {value}"
    if p.kind == "choice" and value not in (p.choices or ()):
        known = ", ".join(map(str, p.choices or ()))
        return f"{name} must be one of {known}, not {value}"
    return None


def check(described, values):
    """Raise ValueError naming the first parameter whose value does not suit it (the task names the step)."""
    for p in described:
        why = problem(p, values.get(p.name))
        if why:
            raise ValueError(why)
