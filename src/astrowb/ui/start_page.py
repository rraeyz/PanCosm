"""The main window's content: a menu of blocks, one per area, each opening that area (in its own window once the
area has moved there, plans/interface.md I4), with the project and a "Continue where you left off" list on top —
as NINA's area tabs with an icon and a short name, but each area its own window."""

from datetime import UTC
from pathlib import Path

from PySide6.QtCore import QT_TRANSLATE_NOOP, QCoreApplication, QEvent, QSize, Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..brand import BRAND
from .kit.icons import icon as area_icon
from .kit.widgets import _title

AREAS = [  # (key, symbol, name, what it does), in the order of the work through a night
    ("plan", "☾", QT_TRANSLATE_NOOP("Areas", "Planning"),
     QT_TRANSLATE_NOOP("Areas", "Visibility, airmass, the Moon, eclipses and transits of the night")),
    ("observe", "⌖", QT_TRANSLATE_NOOP("Areas", "Observing"),
     QT_TRANSLATE_NOOP("Areas", "Telescope, camera, focuser and guider; sequences and whole nights")),
    ("calibrate", "◐", QT_TRANSLATE_NOOP("Areas", "Calibration"),
     QT_TRANSLATE_NOOP("Areas", "Bias, dark and flat frames: masters and calibrated images")),
    ("image", "▣", QT_TRANSLATE_NOOP("Areas", "Images"),
     QT_TRANSLATE_NOOP("Areas", "Look at images and headers, measure, process, stack")),
    ("photometry", "✦", QT_TRANSLATE_NOOP("Areas", "Photometry"),
     QT_TRANSLATE_NOOP("Areas", "Brightness of stars on a series of images: the light curve")),
    ("timeseries", "∿", QT_TRANSLATE_NOOP("Areas", "Light curves and period"),
     QT_TRANSLATE_NOOP("Areas", "Periods, frequencies, variable stars in a set of frames")),
    ("oc", "⊶", QT_TRANSLATE_NOOP("Areas", "O−C"),
     QT_TRANSLATE_NOOP("Areas", "Times of minimum, ephemeris, O−C diagram, third body, apsidal motion")),
    ("spectroscopy", "≋", QT_TRANSLATE_NOOP("Areas", "Spectroscopy"),
     QT_TRANSLATE_NOOP("Areas", "Reduce spectra, wavelengths, radial velocities, orbits")),
    ("orbits", "◎", QT_TRANSLATE_NOOP("Areas", "Models"),
     QT_TRANSLATE_NOOP("Areas", "Eclipsing binaries, visual orbits, light-curve models")),
    ("remotesensing", "◍", QT_TRANSLATE_NOOP("Areas", "Remote sensing"),
     QT_TRANSLATE_NOOP("Areas", "Satellite images: bands, indices, classes")),
    ("automation", "⟳", QT_TRANSLATE_NOOP("Areas", "Automation"),
     QT_TRANSLATE_NOOP("Areas", "Chain steps into a pipeline and run it in one go")),
]  # fmt: skip


def areas():
    """[(key, symbol, name, what it does)] in the interface language."""
    t = QCoreApplication.translate
    return [(key, symbol, t("Areas", name), t("Areas", what)) for key, symbol, name, what in AREAS]


class StartPage(QWidget):
    """The project, the work to continue, and one block per area."""

    action = Signal(str)  # "new_project" | "open_project" | "open_fits" | area key
    resume = Signal(str, str)  # (kind, path): "project" or an area key, and the file to open
    mode_chosen = Signal(str)  # "basic" | "expert"
    tonight_ready = Signal(str)  # the Tonight line, computed off the GUI thread

    def __init__(self, parent=None, mode="basic", recent=()):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.addWidget(_title(self.tr("Welcome to {app}").format(app=BRAND.display_name), self))
        # one row: the project on the left, Basic / Expert on the right (the blocks need the height)
        self.top = top = QHBoxLayout()
        self.project_row, self.mode_row = QHBoxLayout(), QHBoxLayout()
        self.buttons = []
        for title, hint, key in (
            (self.tr("New project"), self.tr("Keep frames, settings and results together"), "new_project"),
            (self.tr("Open project…"), self.tr("Continue earlier work"), "open_project"),
            (self.tr("Open a FITS image"), self.tr("Look at an image and its header"), "open_fits"),
        ):
            button = QPushButton(title, self)
            button.setObjectName(f"start_{key}")
            button.setToolTip(hint)
            button.clicked.connect(lambda _=False, k=key: self.action.emit(k))
            self.project_row.addWidget(button)
            self.buttons.append(button)
        self.project_row.addStretch(1)
        self.mode_row.addWidget(QLabel(self.tr("Interface:"), self))
        basic_text = self.tr("Basic — the main steps; the rarely changed options folded")
        expert_text = self.tr("Expert — every option open")
        tip = self.tr(
            "Nothing is removed in Basic mode: the folded sections open with one click. Change it here or in the "
            "Settings menu at any time."
        )
        self.basic = QRadioButton(basic_text.split(" — ")[0], self)
        self.expert = QRadioButton(expert_text.split(" — ")[0], self)
        for b, key, text in ((self.basic, "basic", basic_text), (self.expert, "expert", expert_text)):
            b.setToolTip(f"{text}\n{tip}")
            b.toggled.connect(lambda on, k=key: self.mode_chosen.emit(k) if on else None)
            self.mode_row.addWidget(b)
        self.mode_row.addStretch(1)
        (self.expert if mode == "expert" else self.basic).setChecked(True)
        top.addLayout(self.project_row, 1)
        top.addLayout(self.mode_row)
        lay.addLayout(top)
        lay.addWidget(self._tonight_label())

        self._continue_cards(lay)
        self.set_recent(recent)

        self.choose = QLabel(self.tr("Choose what you want to do:"), self)
        self.choose.setProperty("muted", True)
        lay.addWidget(self.choose)
        self.grid = QGridLayout()
        self.grid.setSpacing(6)
        self.blocks, self.columns = [], 0
        for key, _symbol, name, what in areas():
            block = QToolButton(self)
            block.setObjectName(f"start_{key}")
            block.setText(f"{name}\n{what}")  # kept for the accessibility name and the tests; drawn by the labels
            block.setToolTip(what)
            block.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            block.setToolButtonStyle(Qt.ToolButtonIconOnly)
            block.setIcon(area_icon(f"area_{key}", self, 48))
            block.setIconSize(QSize(0, 0))  # the icon is drawn by the label beside the name
            inner = QHBoxLayout(block)
            inner.setContentsMargins(8, 2, 8, 2)
            icon = QLabel(block)
            icon.setPixmap(area_icon(f"area_{key}", self, 28).pixmap(28, 28))
            # the description smaller and muted: ten blocks fit a laptop window at 125 % on Windows too
            text = QLabel(f"<b>{name}</b><br><span style='color:gray; font-size:small'>{what}</span>", block)
            text.setTextFormat(Qt.RichText)
            text.setWordWrap(True)
            for label in (icon, text):
                label.setAttribute(Qt.WA_TransparentForMouseEvents)  # the click goes to the block
            inner.addWidget(icon)
            inner.addWidget(text, 1)
            block.setMinimumHeight(2 * text.fontMetrics().lineSpacing() + 6)  # the name and one line of text
            block.label = text
            block.clicked.connect(lambda _=False, k=key: self.action.emit(k))
            self.blocks.append(block)
        self._arrange(1)
        lay.addLayout(self.grid)
        lay.addStretch(1)

    def _continue_cards(self, lay):
        self.continue_label = QLabel(self.tr("Continue where you left off:"), self)
        self.continue_list = QListWidget(self)
        self.continue_list.setToolTip(self.tr("Click to open it again"))
        self.continue_list.setFlow(QListWidget.LeftToRight)  # cards side by side, wrapping
        self.continue_list.setWrapping(True)
        self.continue_list.setIconSize(QSize(28, 28))
        self.continue_list.setGridSize(QSize(260, 52))
        self.continue_list.itemClicked.connect(lambda item: self.resume.emit(*item.data(Qt.UserRole)))
        self.continue_list.itemActivated.connect(lambda item: self.resume.emit(*item.data(Qt.UserRole)))
        lay.addWidget(self.continue_label)
        lay.addWidget(self.continue_list)

    def _tonight_label(self):
        self.tonight = QLabel(self)
        self.tonight.setProperty("muted", True)
        self.tonight.setHidden(True)
        self.tonight.linkActivated.connect(self.action.emit)  # the hint's link: Settings → Profiles
        self.tonight_ready.connect(self.set_tonight)
        return self.tonight

    def show_offline(self, on):
        """A banner while Settings → Work offline is on: catalogues and look-ups then answer only from what was
        fetched before, which looks like "not found" when forgotten (UI-5 item 5)."""
        if on and getattr(self, "offline_banner", None) is None:
            from .kit.banners import InfoBanner

            text = self.tr("Working offline: catalogues, archives and look-ups answer only from what was fetched "
                           "before (Settings → Work offline).")  # fmt: skip
            self.offline_banner = InfoBanner("attention", text, parent=self)
            self.layout().insertWidget(1, self.offline_banner)
        if getattr(self, "offline_banner", None) is not None:
            self.offline_banner.setVisible(on)

    def set_tonight(self, text):
        self.tonight.setText(text)
        self.tonight.setVisible(bool(text))

    def show_tonight(self, settings):
        """The Tonight line when a site is set up (computed in a thread: astropy takes a second), else the hint."""
        from ..core import profiles

        if not profiles.has(settings, "site"):
            hint = self.tr("Set up your site to see tonight's sky")
            self.set_tonight(f'<a href="profiles">{hint}</a>')  # Settings → Profiles
            return
        site = profiles.section(settings, "site")
        import threading

        def work():
            text = self._tonight_text(site)
            try:
                self.tonight_ready.emit(text)
            except RuntimeError:  # the window was closed meanwhile
                pass

        threading.Thread(target=work, daemon=True).start()

    def _tonight_text(self, site):
        from ..planning.visibility import Site, tonight

        try:
            night = tonight(Site(site["name"], site["lat"], site["lon"], site["height"]))
        except Exception:  # noqa: BLE001 — a line of the start window never stops the program
            return ""

        def clock(t):
            return t.to_datetime(UTC).astimezone().strftime("%H:%M") if t is not None else "—"

        return self.tr("Tonight at {site}: dark {dusk}–{dawn} · Moon {moon} %").format(
            site=site["name"] or self.tr("your site"), dusk=clock(night["dusk"]), dawn=clock(night["dawn"]),
            moon=round(100 * night["moon"]))  # fmt: skip

    def set_recent(self, recent):
        """recent: [(kind, path)] — "project" or an area key — newest first; missing files are left out."""
        self.continue_list.clear()
        names = {key: name for key, _, name, _ in areas()}
        names["project"] = self.tr("Project")
        from PySide6.QtCore import QDateTime, QLocale

        from .kit.icons import ICONS

        for kind, path in [(k, p) for k, p in recent if Path(p).exists()][: self.CARDS]:
            when = QLocale().toString(
                QDateTime.fromSecsSinceEpoch(int(Path(path).stat().st_mtime)), QLocale.ShortFormat
            )
            # a card: the area's icon, the file, the area and when it was last saved
            item = QListWidgetItem(f"{Path(path).name}\n{names.get(kind, kind)} · {when}", self.continue_list)
            item.setIcon(area_icon(f"area_{kind}" if f"area_{kind}" in ICONS else "open_folder", self, 28))
            item.setData(Qt.UserRole, (kind, str(path)))
            item.setToolTip(str(path))
        n = self.continue_list.count()
        self.continue_list.setFixedHeight(52 * (1 if n <= 3 else 2) + 8)  # one row of cards, two from four on
        empty = n == 0
        self.continue_label.setHidden(empty)
        self.continue_list.setHidden(empty)

    MIN_COLUMN = 300
    CARDS = 6  # the most recent work shown

    def _arrange(self, columns):
        """Two columns of blocks where they fit, one on a narrow window."""
        if columns != self.columns:
            self.columns = columns
            for i, block in enumerate(self.blocks):
                self.grid.addWidget(block, i // columns, i % columns)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._relayout()

    def showEvent(self, event):
        super().showEvent(event)
        holder = self.parentWidget()  # a scroll area's viewport: the room really there, even when narrower than us
        if holder is not None and not getattr(self, "_watching", False):
            holder.installEventFilter(self)
            self._watching = True
        self._relayout()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Resize and obj is self.parentWidget():
            self._relayout()
        return super().eventFilter(obj, event)

    def _relayout(self):
        holder = self.parentWidget()
        width = holder.width() if holder is not None else self.width()
        margins = self.layout().contentsMargins()
        room = width - margins.left() - margins.right()
        # two columns once each is wide enough to read (descriptions wrap to a second line): ten blocks in one
        # column were taller than a laptop window at 125 % (1100 x 600)
        self._arrange(2 if room >= 2 * self.MIN_COLUMN + self.grid.horizontalSpacing() else 1)
        # the project buttons and Basic / Expert side by side when they fit, else one row under the other
        buttons = sum(b.sizeHint().width() for b in self.buttons) + 2 * self.project_row.spacing()
        self.project_row.setDirection(QHBoxLayout.LeftToRight if room >= buttons else QHBoxLayout.TopToBottom)
        wide = self.project_row.sizeHint().width() + self.mode_row.sizeHint().width() + 24
        self.top.setDirection(QHBoxLayout.LeftToRight if room >= wide else QHBoxLayout.TopToBottom)
        column = (room - (self.columns - 1) * self.grid.horizontalSpacing()) // self.columns
        for b in self.blocks:  # tall enough for the description as it wraps at this width
            b.setMinimumHeight(b.label.heightForWidth(max(80, column - 28 - 32)) + 6)
