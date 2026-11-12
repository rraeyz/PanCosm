"""The words a user reads for the engine's steps, settings and inputs instead of their ids and keys; the ids stay in
tooltips and saved files. Everything comes from the engine's own descriptions (AUT-1 item 4): step titles from
engine.titles, settings from engine.params, inputs from engine.io."""

from PySide6.QtCore import QCoreApplication


def step_name(step_id):
    """The step's title in the interface language; a step without one (a plugin's) keeps its id."""
    from ..engine.titles import TITLES

    base = str(step_id).split(" ")[0]  # a task name may carry more after the id
    if base not in TITLES:
        return str(step_id)
    return QCoreApplication.translate("Steps", TITLES[base]) + str(step_id)[len(base) :]


def setting_name(step_id, key):
    """The setting's or input's name in the interface language; one without a description (a plugin's) is its key
    with spaces."""
    from ..engine import io, steps

    try:
        described = {p.name: p for p in steps.get(step_id).params}
    except KeyError:
        described = {}
    p = described.get(key)
    if p is not None and p.label:
        name = QCoreApplication.translate("Steps", p.label)
        return f"{name} ({p.unit})" if p.unit else name
    put = io.describe(step_id, key)
    return QCoreApplication.translate("Steps", put.label) if put else str(key).replace("_", " ")
