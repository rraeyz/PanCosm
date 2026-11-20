"""The steps of an automation as a vertical chain of cards (plans/interface.md UI-16.12): one card per step with
its title and a one-line summary of its settings; the selected card is the step the inspector shows."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QAbstractButton, QButtonGroup, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget


class StepChain(QScrollArea):
    currentRowChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        body = QWidget(self)
        self._lay = QVBoxLayout(body)
        self._lay.addStretch(1)
        self.setWidget(body)
        self._group = QButtonGroup(self)
        self._group.idToggled.connect(lambda i, on: on and self.currentRowChanged.emit(i))

    def clear(self):
        for b in self._group.buttons():
            self._group.removeButton(b)
        while self._lay.count() > 1:  # the closing stretch stays
            w = self._lay.takeAt(0).widget()
            w.setParent(None)
            w.deleteLater()

    def add_card(self, title, summary, tip):
        """A card below the others, joined to the one above by an arrow."""
        n = self._group.buttons().__len__()
        if n:
            arrow = QLabel("↓", self)
            arrow.setAlignment(Qt.AlignHCenter)
            self._lay.insertWidget(self._lay.count() - 1, arrow)
        card = QPushButton(self)
        card.setProperty("title", title)
        card.setText(f"{title}\n{summary}" if summary else title)
        card.setCheckable(True)
        card.setToolTip(tip)
        card.setStyleSheet("text-align: left; padding: 6px;")
        self._group.addButton(card, n)
        self._lay.insertWidget(self._lay.count() - 1, card)

    def set_summary(self, row, summary):
        card = self._group.button(row)
        if card is not None:
            title = card.property("title")
            card.setText(f"{title}\n{summary}" if summary else title)

    def count(self):
        return len(self._group.buttons())

    def currentRow(self):
        return self._group.checkedId()

    def setCurrentRow(self, row):
        button = self._group.button(row)
        if isinstance(button, QAbstractButton):
            button.setChecked(True)
