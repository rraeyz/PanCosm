"""The main window's content: a menu of blocks, one per area, each opening that area (in its own window once the
area has moved there, plans/interface.md I4), with the project and a "Continue where you left off" list on top —
as NINA's area tabs with an icon and a short name, but each area its own window."""

from pathlib import Path

from PySide6.QtCore import QT_TRANSLATE_NOOP, QCoreApplication, QSize, Qt, Signal
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
from .widgets import _title, glyph

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
    ("timeseries", "∿", QT_TRANSLATE_NOOP("Areas", "Light curves, period and O−C"),
     QT_TRANSLATE_NOOP("Areas", "Periods, frequencies, times of minimum, O−C")),
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

        self.continue_label = QLabel(self.tr("Continue where you left off:"), self)
        self.continue_list = QListWidget(self)
        self.continue_list.setToolTip(self.tr("Double-click to open it again"))
        self.continue_list.setMaximumHeight(100)
        self.continue_list.itemActivated.connect(lambda item: self.resume.emit(*item.data(Qt.UserRole)))
        lay.addWidget(self.continue_label)
        lay.addWidget(self.continue_list)
        self.set_recent(recent)

        lay.addWidget(QLabel(self.tr("Choose what you want to do:"), self))
        self.grid = QGridLayout()
        self.grid.setSpacing(6)
        self.blocks, self.columns = [], 0
        colour = self.palette().windowText().color()
        for key, symbol, name, what in areas():
            block = QToolButton(self)
            block.setObjectName(f"start_{key}")
            block.setText(f"{name}\n{what}")  # kept for the accessibility name and the tests; drawn by the labels
            block.setToolTip(what)
            block.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            block.setToolButtonStyle(Qt.ToolButtonIconOnly)
            block.setIcon(glyph(symbol, colour, 48))
            block.setIconSize(QSize(0, 0))  # the icon is drawn by the label beside the name
            inner = QHBoxLayout(block)
            inner.setContentsMargins(8, 4, 8, 4)
            icon = QLabel(block)
            icon.setPixmap(glyph(symbol, colour, 48).pixmap(28, 28))
            text = QLabel(f"<b>{name}</b><br><span style='color:gray'>{what}</span>", block)
            text.setTextFormat(Qt.RichText)
            text.setWordWrap(True)
            for label in (icon, text):
                label.setAttribute(Qt.WA_TransparentForMouseEvents)  # the click goes to the block
            inner.addWidget(icon)
            inner.addWidget(text, 1)
            block.setMinimumHeight(2 * text.fontMetrics().lineSpacing() + 14)  # the name and one line of text
            block.label = text
            block.clicked.connect(lambda _=False, k=key: self.action.emit(k))
            self.blocks.append(block)
        self._arrange(1)
        lay.addLayout(self.grid)
        lay.addStretch(1)

    def set_recent(self, recent):
        """recent: [(kind, path)] — "project" or an area key — newest first; missing files are left out."""
        self.continue_list.clear()
        names = {key: name for key, _, name, _ in areas()}
        names["project"] = self.tr("Project")
        for kind, path in recent:
            if Path(path).exists():
                item = QListWidgetItem(f"{Path(path).name}  —  {names.get(kind, kind)}", self.continue_list)
                item.setData(Qt.UserRole, (kind, str(path)))
                item.setToolTip(str(path))
        empty = self.continue_list.count() == 0
        self.continue_label.setHidden(empty)
        self.continue_list.setHidden(empty)

    MIN_COLUMN = 300

    def _arrange(self, columns):
        """Two columns of blocks where they fit, one on a narrow window."""
        if columns != self.columns:
            self.columns = columns
            for i, block in enumerate(self.blocks):
                self.grid.addWidget(block, i // columns, i % columns)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        margins = self.layout().contentsMargins()
        room = event.size().width() - margins.left() - margins.right()
        # two columns once each is wide enough to read (descriptions wrap to a second line): ten blocks in one
        # column were taller than a laptop window at 125 % (1100 x 600)
        self._arrange(2 if room >= 2 * self.MIN_COLUMN + self.grid.horizontalSpacing() else 1)
        # the project buttons and Basic / Expert side by side when they fit, else one row under the other
        wide = self.project_row.minimumSize().width() + self.mode_row.minimumSize().width() + 24
        self.top.setDirection(QHBoxLayout.LeftToRight if room >= wide else QHBoxLayout.TopToBottom)
        column = (room - (self.columns - 1) * self.grid.horizontalSpacing()) // self.columns
        for b in self.blocks:  # tall enough for the description as it wraps at this width
            b.setMinimumHeight(b.label.heightForWidth(max(80, column - 28 - 32)) + 10)
