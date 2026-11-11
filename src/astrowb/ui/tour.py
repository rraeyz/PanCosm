"""A short guided tour shown once after the first start: where the pages and the main controls are.
An overlay darkens the window except the highlighted part and shows a short text with Next / Skip.
Help → Quick tour shows it again."""

from PySide6.QtCore import QCoreApplication, QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QDockWidget, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


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


translate = QCoreApplication.translate  # pyside6-lupdate reads translate("MainWindow", "…") calls


def start(main):
    """Short guided tour of the pages and the main controls."""
    from .tour import TourOverlay, rect_of

    steps = _steps(main, rect_of)
    main.tour = TourOverlay(main, steps)
    main.tour.start()
    main.settings.set("ui.tour_done", True)
    return main.tour


def _steps(main, rect_of):
    """The tour's stops: (where, text)."""
    from PySide6.QtWidgets import QToolButton

    def item(key):  # the area's block on the start page
        return lambda: rect_of(main.start_page.findChild(QToolButton, f"start_{key}"), main)

    def blocks():
        shown = [rect_of(b, main) for b in main.start_page.blocks]
        shown = [r for r in shown if r is not None]
        return shown[0].united(shown[-1]) if shown else None

    main.show_workspace("start")
    dock = main.findChild(QDockWidget, "tasks")
    return [
        (
            None,
            translate(
                "MainWindow", "Welcome! This one-minute tour shows where things are. Press Next, or Skip at any time."
            ),
        ),
        (
            blocks,
            translate(
                "MainWindow", "The areas, in the order of an observing night. Click one to open it in its window."
            ),
        ),
        (
            lambda: rect_of(main.start_page, main),
            translate(
                "MainWindow",
                "Start here: pick what you have — raw frames, images, spectra, a list of minima — and its window opens.",  # noqa: E501
            ),
        ),
        (
            item("plan"),
            translate(
                "MainWindow",
                "Planning: when your targets are visible, airmass, the Moon, predicted eclipses and transits.",
            ),
        ),
        (
            item("observe"),
            translate(
                "MainWindow",
                "Observing: connect the telescope and camera, run sequences and whole nights. The safety supervisor parks the telescope when something is wrong.",  # noqa: E501
            ),
        ),
        (
            item("calibrate"),
            translate(
                "MainWindow",
                "Calibration: bias, dark and flat frames are matched and applied automatically; frames can be aligned and stacked.",  # noqa: E501
            ),
        ),
        (
            item("photometry"),
            translate(
                "MainWindow",
                "Photometry, then Light curves and period and O−C: measure stars, get light curves, periods, minima and O−C diagrams.",  # noqa: E501
            ),
        ),
    ] + _later_steps(main, rect_of, dock)


def _later_steps(main, rect_of, dock):
    """The second half of the tour's stops."""

    def item(key):  # the area's block on the start page
        from PySide6.QtWidgets import QToolButton

        return lambda: rect_of(main.start_page.findChild(QToolButton, f"start_{key}"), main)

    return [
        (
            item("spectroscopy"),
            translate(
                "MainWindow",
                "Spectroscopy: long-slit and echelle reduction, telluric correction, radial velocities, IFU cubes.",
            ),
        ),
        (
            item("orbits"),
            translate(
                "MainWindow",
                "Models: eclipsing-binary and transit light-curve models, absolute dimensions and visual orbits.",
            ),
        ),
        (
            item("remotesensing"),
            translate(
                "MainWindow",
                "Remote sensing: satellite and aerial images — band math, vegetation and water indices, classes.",
            ),
        ),
        (
            item("automation"),
            translate(
                "MainWindow",
                "Automation: chain steps into your own pipeline or start from a ready template (eclipsing binary night, transit, calibration, spectra to RV) and run it in one go.",  # noqa: E501
            ),
        ),
        (
            lambda: rect_of(main.menuBar(), main),  # the guide has no block: Help → Training guide opens it
            translate(
                "MainWindow",
                "Guide: every window explained step by step, by category, with search. Help → Training guide opens it; F1 in a window opens its own page.",  # noqa: E501
            ),
        ),
        (
            lambda: rect_of(dock, main),
            translate(
                "MainWindow", "Tasks: long jobs run here in the background with their progress; you can keep working."
            ),
        ),
        (
            lambda: rect_of(main.menuBar(), main),
            translate(
                "MainWindow",
                "Menus: Plugins for your own tools, Settings for language, look and CPU/GPU, Help for this tour and the guide; each area's window has its own menus and toolbar.",  # noqa: E501
            ),
        ),
        (
            lambda: rect_of(main.menuBar(), main),  # Help → Practice data is there
            translate(
                "MainWindow",
                "In every area window: the stages on the left (Ctrl+1…9), F5 runs the stage's main action, F1 or Shift+F1 opens help, Ctrl+K finds any action, Ctrl+/ lists every key. To try it all, Help → Practice data for a first night gives data with known answers.",  # noqa: E501
            ),
        ),
    ]
