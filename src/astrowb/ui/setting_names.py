"""The name a user reads for each setting and input of a step in the Automation window, instead of its key
("clock_utc_offset"); the key stays in the tooltip and in saved files. The names come from the steps' own
descriptions (AUT-1 item 4): settings from engine.params, inputs from engine.io."""

from PySide6.QtCore import QCoreApplication


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
