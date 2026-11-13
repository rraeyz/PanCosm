"""Panels that fit their width (user feedback UF-9, UF-10): an opened fold pushed the Photometry stage and the
Calibration options past the window's right edge, in every language and even full screen. fit_width(root, limit)
makes a built panel narrow-friendly without touching how each page builds it:

- a combo box takes the width of ten characters, not of its longest choice (the list still shows each whole);
- a check box whose text is wider than the limit keeps its box, and its text becomes a label beside it that wraps
  (a click on the label still toggles it; it greys out with the box);
- a row of two or more widgets wider than the limit flows onto the next line instead.
"""

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QBoxLayout, QCheckBox, QComboBox, QHBoxLayout, QLabel, QLayout, QSizePolicy, QWidget


class FlowLayout(QLayout):
    """Widgets left to right, onto the next line when the width runs out (Qt's flow-layout example)."""

    def __init__(self, parent=None, spacing=6):
        super().__init__(parent)
        self._items = []
        self.setSpacing(spacing)
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item):  # noqa: N802 (Qt's name)
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, i):  # noqa: N802
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i):  # noqa: N802
        return self._items.pop(i) if 0 <= i < len(self._items) else None

    def expandingDirections(self):  # noqa: N802
        return Qt.Orientation(0)

    def hasHeightForWidth(self):  # noqa: N802
        return True

    def heightForWidth(self, width):  # noqa: N802
        return self._place(QRect(0, 0, width, 0), move=False)

    def setGeometry(self, rect):  # noqa: N802
        super().setGeometry(rect)
        self._place(rect, move=True)

    def sizeHint(self):  # noqa: N802
        return self.minimumSize()

    def minimumSize(self):  # noqa: N802
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        return size

    def _place(self, rect, move):
        x, y, line = rect.x(), rect.y(), 0
        for item in self._items:
            hint = item.sizeHint()
            if x + hint.width() > rect.right() and line > 0:
                x, y, line = rect.x(), y + line + self.spacing(), 0
            if move:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x += hint.width() + self.spacing()
            line = max(line, hint.height())
        return y + line - rect.y()


class _LabelToggles(QObject):
    """A click on the wrapped text toggles its box; the text greys out with the box."""

    def __init__(self, box, label):
        super().__init__(label)
        self.box, self.label = box, label

    def eventFilter(self, obj, event):  # noqa: N802
        if obj is self.label and event.type() == QEvent.MouseButtonRelease and self.box.isEnabled():
            self.box.toggle()
            return True
        if obj is self.box and event.type() == QEvent.EnabledChange:
            self.label.setEnabled(self.box.isEnabled())
        if obj is self.box and event.type() == QEvent.ToolTipChange:
            self.label.setToolTip(self.box.toolTip())
        return False


def _wrap_check(box):
    parent = box.parentWidget()
    lay = parent.layout() if parent is not None else None
    holder_lay = _layout_holding(lay, box) if lay is not None else None
    if holder_lay is None:
        return
    holder = QWidget(parent)
    row = QHBoxLayout(holder)
    row.setContentsMargins(0, 0, 0, 0)
    label = QLabel(box.text(), holder)
    label.setWordWrap(True)
    label.setToolTip(box.toolTip())
    label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
    label.setMinimumWidth(120)
    box.setProperty("full_text", box.text())
    box.setAccessibleName(box.text())  # screen readers and the walks still find it by its words
    holder_lay.replaceWidget(box, holder)
    box.setText("")
    row.addWidget(box, 0, Qt.AlignTop)
    row.addWidget(label, 1)
    toggles = _LabelToggles(box, label)
    label.installEventFilter(toggles)
    box.installEventFilter(toggles)
    label.setEnabled(box.isEnabled())


def _layout_holding(lay, widget):
    """The layout (lay or one nested in it) that holds widget directly."""
    if lay.indexOf(widget) >= 0:
        return lay
    for i in range(lay.count()):
        inner = lay.itemAt(i).layout()
        if inner is not None and (found := _layout_holding(inner, widget)) is not None:
            return found
    return None


def _flow(row):
    """A too-wide horizontal row of plain widgets becomes a flowing one, in its place."""
    parent = row.parent()
    if not isinstance(parent, QBoxLayout):
        return
    items = [row.itemAt(i) for i in range(row.count())]
    if any(it.layout() is not None for it in items):
        return  # rows holding rows stay as they are
    index = next((i for i in range(parent.count()) if parent.itemAt(i).layout() is row), None)
    owner = parent.parentWidget()
    if index is None or owner is None:
        return
    holder = QWidget(owner)
    flow = FlowLayout(holder)
    widgets = [it.widget() for it in items if it.widget() is not None]
    parent.removeItem(row)
    for w in widgets:
        row.removeWidget(w)
        flow.addWidget(w)
    holder.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
    parent.insertWidget(index, holder)
    row.setParent(None)


def fit_width(root, limit):
    for box in root.findChildren(QComboBox):
        box.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        box.setMinimumContentsLength(10)
    for box in root.findChildren(QCheckBox):
        if box.text() and box.sizeHint().width() > limit:
            _wrap_check(box)
    for row in root.findChildren(QHBoxLayout):
        if row.count() >= 2 and row.minimumSize().width() > limit:
            _flow(row)
