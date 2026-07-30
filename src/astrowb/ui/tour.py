"""A short guided tour shown once after the first start: where the pages and the main controls are.
An overlay darkens the window except the highlighted part and shows a short text with Next / Skip.
Help → Quick tour shows it again."""

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class TourOverlay(QWidget):
    def __init__(self, window, steps):
        """steps: [(callable returning a QRect in window coordinates (or None), text), ...]"""
        super().__init__(window)
        self.window_, self.steps, self.index = window, steps, 0
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.bubble = QWidget(self)
        self.bubble.setObjectName("tourBubble")
        self.bubble.setStyleSheet(
            "#tourBubble { background: palette(base); border: 1px solid palette(highlight); border-radius: 10px; }"
        )
        lay = QVBoxLayout(self.bubble)
        self.count = QLabel(self.bubble)
        self.count.setProperty("muted", True)
        self.text = QLabel(self.bubble)
        self.text.setWordWrap(True)
        self.text.setMinimumWidth(320)
        lay.addWidget(self.count)
        lay.addWidget(self.text)
        row = QHBoxLayout()
        self.skip = QPushButton(self.tr("Skip tour"), self.bubble)
        self.skip.clicked.connect(self.finish)
        self.next = QPushButton(self.tr("Next"), self.bubble)
        self.next.setProperty("primary", True)
        self.next.clicked.connect(self.advance)
        row.addWidget(self.skip)
        row.addStretch(1)
        row.addWidget(self.next)
        lay.addLayout(row)
        self.finished = False
        window.installEventFilter(self)

    def start(self):
        self.setGeometry(self.window_.rect())
        self.show()
        self.raise_()
        self._show_step()

    def eventFilter(self, obj, event):
        if obj is self.window_ and event.type() == event.Type.Resize:
            self.setGeometry(self.window_.rect())
            self._place()
        return False

    def _rect(self):
        get, _ = self.steps[self.index]
        r = get() if get else None
        return r.adjusted(-4, -4, 4, 4) if r is not None and not r.isNull() else None

    def _show_step(self):
        _, text = self.steps[self.index]
        self.count.setText(self.tr("{i} of {n}").format(i=self.index + 1, n=len(self.steps)))
        self.text.setText(text)
        last = self.index == len(self.steps) - 1
        self.next.setText(self.tr("Done") if last else self.tr("Next"))
        self._place()
        self.update()

    def _place(self):
        self.bubble.adjustSize()
        r, b = self._rect(), self.bubble.size()
        w, h = self.width(), self.height()
        if r is None:
            x, y = (w - b.width()) // 2, (h - b.height()) // 2
        elif r.right() + 16 + b.width() < w:  # to the right of the highlighted part
            x, y = r.right() + 16, r.top()
        elif r.bottom() + 16 + b.height() < h:  # below it
            x, y = r.left(), r.bottom() + 16
        else:  # above it
            x, y = r.left(), r.top() - 16 - b.height()
        self.bubble.move(max(8, min(x, w - b.width() - 8)), max(8, min(y, h - b.height() - 8)))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRect(self.rect())
        r = self._rect()
        if r is not None:
            hole = QPainterPath()
            hole.addRoundedRect(r, 8, 8)
            path = path.subtracted(hole)
        p.fillPath(path, QColor(0, 0, 0, 150))
        if r is not None:
            p.setPen(self.palette().highlight().color())
            p.drawRoundedRect(r, 8, 8)

    def advance(self):
        if self.index >= len(self.steps) - 1:
            return self.finish()
        self.index += 1
        self._show_step()

    def finish(self):
        self.finished = True
        self.window_.removeEventFilter(self)
        self.hide()
        self.deleteLater()


def rect_of(widget, window):
    """A widget's rectangle in window coordinates (None when hidden)."""
    if widget is None or not widget.isVisible():
        return None
    return QRect(widget.mapTo(window, widget.rect().topLeft()), widget.size())
