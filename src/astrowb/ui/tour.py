"""A short guided tour shown once after the first start: where the pages and the main controls are.
An overlay darkens the window except the highlighted part and shows a short text with Next / Skip.
Help → Quick tour shows it again."""

from PySide6.QtCore import QCoreApplication, QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class TourOverlay(QWidget):
    def __init__(self, window, steps, offer=None):
        """steps: [(callable returning a QRect in window coordinates (or None), text), ...];
        offer: (label, callback) shown as a button on the last step, which ends the tour and calls back."""
        super().__init__(window)
        self.window_, self.steps, self.index, self.offer = window, steps, 0, offer
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
        self.offer_button = QPushButton(offer[0] if offer else "", self.bubble)
        self.offer_button.clicked.connect(self._take_offer)
        row.addWidget(self.offer_button)
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
        self.offer_button.setVisible(last and self.offer is not None)
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

    def _take_offer(self):
        self.finish()
        self.offer[1]()

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
    """The quick tour (UI-19): six stops on the start window, the last one offering the practice night."""
    from .tour import TourOverlay, rect_of

    offer = (translate("MainWindow", "Practice night in five minutes"), lambda: _practice_night(main))
    main.tour = TourOverlay(main, _steps(main, rect_of), offer)
    main.tour.start()
    main.settings.set("ui.tour_done", True)
    return main.tour


def _practice_night(main):
    """Make the practice data, then open guided task 1 (first-night.toml) on it."""
    from . import help_checks
    from .kit import guided

    def begin():
        task = next(t for t in guided.available(main.settings.get("ui.language", "en")) if "first-night" in t["path"])
        help_checks.start_guided(main, task)

    main.practice_data(then=begin)


def _steps(main, rect_of):
    """The tour's six stops: (where, text)."""
    from PySide6.QtWidgets import QToolButton

    def photometry():  # an area's block: opening one gives the window the next three stops talk about
        return rect_of(main.start_page.findChild(QToolButton, "start_photometry"), main)

    def blocks():
        shown = [rect_of(b, main) for b in main.start_page.blocks]
        shown = [r for r in shown if r is not None]
        return shown[0].united(shown[-1]) if shown else None

    def menus():  # Help is in the menu bar
        return rect_of(main.menuBar(), main)

    main.show_workspace("start")
    return [
        (blocks, translate("MainWindow", "The areas, in the order of an observing night. Click one to open it in its "
                           "own window.")),
        (photometry, translate("MainWindow", "In an area's window the stages of the work are on the left, in order. A "
                               "stage done gets ✓ and the next opens by itself; Ctrl+1…9 jumps to one.")),
        (photometry, translate("MainWindow", "Each stage has one main button: F5 presses it, and while it works the "
                               "button shows its progress and becomes Stop (Esc).")),
        (photometry, translate("MainWindow", "What the work produces appears in the results panel, in tabs; a row or a "
                               "point shows its frame or star.")),
        (menus, translate("MainWindow", "F1 opens the help page of the stage you are in; Help → Training guide has "
                          "every window explained.")),
        (menus, translate("MainWindow", "Ctrl+K finds any action by its name, in every window; Ctrl+/ lists every "
                          "key. To try it all, take the practice night: data with known answers, ready in five "
                          "minutes.")),
    ]  # fmt: skip


def start_area(win):
    """The tour of an area window's own anatomy (UI-19): stages, the stage's controls, the main view, the results,
    the toolbar and the keys. Stops whose part the window does not have are left out."""
    from PySide6.QtWidgets import QDockWidget

    def dock(name):
        d = win.findChild(QDockWidget, name)
        return d if d is not None and d.isVisible() else None

    parts = [
        (getattr(win, "rail", None), translate("MainWindow", "The stages of the work, in order. A stage done gets ✓ "
                                               "and the next opens by itself; Ctrl+1…9 jumps to one.")),
        (getattr(win, "stage_stack", None), translate("MainWindow", "The chosen stage's controls. Its ? opens the "
                                                      "guide's page for it; F5 runs its main action.")),
        (win.centralWidget(), translate("MainWindow", "The main view: the image, the chart or the table you work "
                                        "on.")),
        (dock("results"), translate("MainWindow", "Results: what the work produced, in tabs; a row or point shows "
                                    "its frame or star.")),
        (win.toolbar, translate("MainWindow", "The toolbar: the window's main actions. View → Toolbar text writes "
                                "their names beside the icons.")),
        (win.menuBar(), translate("MainWindow", "Every action is also in the menus; Ctrl+K finds any of them by name "
                                  "and Ctrl+/ lists every key.")),
    ]  # fmt: skip
    steps = [(lambda w=w: rect_of(w, win), text) for w, text in parts if w is not None and w.isVisible()]
    win.tour = TourOverlay(win, steps)
    win.tour.start()
    return win.tour
