"""The steps of an automation as a vertical chain of cards (plans/interface.md UI-16.12): one card per step with
its title and a one-line summary of its settings; the selected card is the step the inspector shows."""

from PySide6.QtCore import QCoreApplication, QMimeData, Qt, Signal
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .kit.banners import Badge
from .step_library import STEP_MIME

CARD_MIME = "application/x-astrowb-card"


class _Card(QPushButton):
    """A card that can be dragged to another place in the chain (its row travels in the mime data)."""

    def __init__(self, chain):
        super().__init__(chain)
        self.chain, self._press = chain, None

    def mousePressEvent(self, event):
        self._press = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._press is not None and (event.position().toPoint() - self._press).manhattanLength() > 12:
            self._press = None
            mime = QMimeData()
            mime.setData(CARD_MIME, str(self.chain._group.id(self)).encode())
            drag = QDrag(self)
            drag.setMimeData(mime)
            drag.exec(Qt.MoveAction)
        else:
            super().mouseMoveEvent(event)


class StepChain(QScrollArea):
    currentRowChanged = Signal(int)
    runFromHere = Signal(int)  # the card's right-click action: run the chain starting at this card
    stepDropped = Signal(str, int)  # a library step dropped: step id, the place it goes to
    cardMoved = Signal(int, int)  # a card dropped: its row, the place it goes to (before the card now there)

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
        self.viewport().setAcceptDrops(True)

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
        card = _Card(self)
        card.setProperty("title", title)
        card.setText(f"{title}\n{summary}" if summary else title)
        card.setCheckable(True)
        card.setToolTip(tip)
        card.setStyleSheet("text-align: left; padding: 6px;")
        card.setContextMenuPolicy(Qt.CustomContextMenu)
        card.customContextMenuRequested.connect(lambda pos, c=card: self._menu(c, pos))
        badge = Badge("", "attention", card)  # shown while a required input has no source
        badge.hide()
        row = QHBoxLayout(card)
        row.addStretch(1)
        row.addWidget(badge, 0, Qt.AlignTop)
        card.badge = badge
        self._group.addButton(card, n)
        self._lay.insertWidget(self._lay.count() - 1, card)

    def _menu(self, card, pos):
        menu = QMenu(card)
        menu.addAction(QCoreApplication.translate("StepChain", "Run from here")).triggered.connect(
            lambda: self.runFromHere.emit(self._group.id(card))
        )
        menu.popup(card.mapToGlobal(pos))

    def drop_place(self, pos):
        """The place a drop at `pos` (viewport coordinates) goes to: the number of cards whose middle is above it."""
        y = self.widget().mapFrom(self.viewport(), pos).y()
        return sum(b.geometry().center().y() < y for b in self._group.buttons())

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(STEP_MIME) or event.mimeData().hasFormat(CARD_MIME):
            event.acceptProposedAction()

    dragMoveEvent = dragEnterEvent

    def dropEvent(self, event):
        mime, at = event.mimeData(), self.drop_place(event.position().toPoint())
        if mime.hasFormat(STEP_MIME):
            self.stepDropped.emit(bytes(mime.data(STEP_MIME)).decode(), at)
        elif mime.hasFormat(CARD_MIME):
            self.cardMoved.emit(int(bytes(mime.data(CARD_MIME)).decode()), at)
        else:
            return
        event.acceptProposedAction()

    def set_badge(self, row, text):
        card = self._group.button(row)
        if card is not None:
            card.badge.setText(text)
            card.badge.setVisible(bool(text))

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
