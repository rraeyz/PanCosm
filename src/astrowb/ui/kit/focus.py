"""Tab order that follows the screen (ARC-19): Qt's chain is the order widgets were made in, which is not always the
order they are read in."""

from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtWidgets import QWidget


class _OnShow(QObject):
    def __init__(self, widget, action):
        super().__init__(widget)
        self.action = action
        widget.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Show:
            obj.removeEventFilter(self)
            QTimer.singleShot(0, self.action)  # not inside the event: the widget may be half built
            QTimer.singleShot(0, self.deleteLater)
        return False


def read_in_order(*parts):
    """Make Tab visit the controls of each part (a widget, itself included) one after the other, in the order given.
    Done when the first part is shown: Qt refuses to order widgets that are not in a window yet."""

    def apply():
        controls = []
        for p in filter(None, parts):
            try:
                controls += [c for c in [p, *p.findChildren(QWidget)] if c.focusPolicy() & Qt.TabFocus]
            except RuntimeError:  # a part Qt has deleted since (a form that was rebuilt)
                pass
        for first, second in zip(controls, controls[1:], strict=False):
            if first.window() is second.window():
                QWidget.setTabOrder(first, second)

    if parts[0].isVisible():
        apply()
    else:
        _OnShow(parts[0], apply)
