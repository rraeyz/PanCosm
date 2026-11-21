"""Observing (UI-16.9): a chip per device in the toolbar and the inspector with the selected device's or exposure
row's details. Everything shown comes from the status the page already polls; a field the observatory does not
report is left out."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QToolButton

from .kit.inspector import Inspector
from .kit.tokens import role

translate = QCoreApplication.translate
# device -> the control that shows its stage
DEVICES = {
    "mount": "target",
    "camera": "cooler_temp",
    "focuser": "focus_pos",
    "filterwheel": "filter_name",
    "rotator": None,
    "dome": None,
}


def _name(key):
    return {"mount": translate("ObserveChips", "Mount"), "camera": translate("ObserveChips", "Camera"),
            "focuser": translate("ObserveChips", "Focuser"), "filterwheel": translate("ObserveChips", "Filter wheel"),
            "rotator": translate("ObserveChips", "Rotator"),
            "dome": translate("ObserveChips", "Dome")}[key]  # fmt: skip


def _summary(key, state):
    """(text after the name, busy) from the device's polled values."""
    if key == "camera" and "CCDTemperature" in state:
        return f"{state['CCDTemperature']:.1f} °C", False
    if key == "focuser" and "Position" in state:
        return str(state["Position"]), bool(state.get("IsMoving"))
    if key == "filterwheel" and state.get("Names") and 0 <= state.get("Position", -1) < len(state["Names"]):
        return state["Names"][state["Position"]], False
    if key == "mount" and "parked" in state:
        word = (
            translate("ObserveChips", "parked")
            if state["parked"]
            else (
                translate("ObserveChips", "tracking")
                if state["tracking"]
                else translate("ObserveChips", "not tracking")
            )
        )
        return word, False
    return "", False


class ObserveChips:
    def __init__(self, win, page):
        self.win, self.page, self.chips, self.state = win, page, {}, {}
        self.inspector = Inspector(translate("ObserveChips", "Inspector"), win)
        self.dock = win.set_inspector(self.inspector)
        self.dock.hide()  # shown by the first chip or exposure row clicked: the main view keeps its width
        page.status_arrived.connect(self.update)
        page.exposures.currentCellChanged.connect(lambda *_: self.show_exposure())

    def update(self, st):
        self.state = st
        for key in [k for k in DEVICES if k in st or k in st.get("devices", {})]:
            state = st.get(key, {})
            chip = self.chips.get(key) or self._new(key)
            text, busy = _summary(key, state)
            chip.setText(f"{_name(key)} {text}".strip())
            lost = "error" in state
            colour = role("saturated") if lost else role("non_linear") if busy else ""
            chip.setStyleSheet(f"color: {colour};" if colour else "")

    def _new(self, key):
        chip = QToolButton(self.win.toolbar)
        chip.setAutoRaise(True)
        chip.clicked.connect(lambda _on=False, k=key: self.show_device(k))
        self.win.toolbar.addWidget(chip)
        self.chips[key] = chip
        return chip

    def show_device(self, key):
        """The stage with the device's controls, and its values in the inspector."""
        control = getattr(self.page, DEVICES[key] or "", None)
        for stage, panel in self.win.stage_panels.items():
            if control is not None and panel.isAncestorOf(control):
                self.win.show_stage(stage)
        st = self.state
        rows = [(k, v, "") for k, v in st.get(key, {}).items() if k != "error" and not isinstance(v, dict)]
        if key in st.get("devices", {}):
            rows.append((translate("ObserveChips", "Last answer"), st["devices"][key], "s ago"))
        self.inspector.set_title(_name(key))
        self.inspector.set_rows(rows)
        self.dock.show()

    def show_exposure(self):
        t, r = self.page.exposures, self.page.exposures.currentRow()
        if r < 0:
            return
        item = t.item(r, 1)
        rows = [(translate("ObserveChips", "Kind"), t.cellWidget(r, 0).currentText(), ""),
                (translate("ObserveChips", "Filter"), item.text().strip() if item else "", ""),
                (translate("ObserveChips", "Exposure"), t.cellWidget(r, 2).value(), "s"),
                (translate("ObserveChips", "Count"), t.cellWidget(r, 3).value(), ""),
                (translate("ObserveChips", "Binning"), t.cellWidget(r, 4).value(), "")]  # fmt: skip
        self.inspector.set_title(translate("ObserveChips", "Exposure row {n}").format(n=r + 1))
        self.inspector.set_rows(rows)
        self.dock.show()
