"""The file strip's thumbnails-or-list switch and "Follow a folder" (UI-16.10). The strip is the page's open list: the
thumbnails are its icons (drawn lazily by the page, once per file), so the switch only changes how the list lays out."""

from pathlib import Path

from PySide6.QtCore import QCoreApplication, QFileSystemWatcher, QSize, QTimer
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QListView, QPushButton, QWidget

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("ImageWindow", "…") calls

FITS_SUFFIXES = (".fits", ".fit", ".fts", ".fits.gz", ".fit.gz")


def set_thumbnails(lst, on):
    """Icon mode with large previews, or today's list; the widget keeps the selection and the current row."""
    lst.setViewMode(QListView.IconMode if on else QListView.ListMode)
    lst.setIconSize(QSize(96, 96) if on else QSize(56, 56))
    lst.setGridSize(QSize(110, 126) if on else QSize())
    lst.setMovement(QListView.Static)
    lst.setResizeMode(QListView.Adjust)
    lst.setWordWrap(on)


def fits_in(folder):
    return sorted(str(p) for p in Path(folder).iterdir() if p.name.lower().endswith(FITS_SUFFIXES))


class FolderFollower:
    """Hands the FITS files that appear in a folder to on_new(paths); by default the page's add_open, looked up at
    call time (the Calibrate stage passes its own)."""

    def __init__(self, page, on_new=None):
        self.page, self.on_new, self.folder, self.seen = page, on_new, None, set()
        self.watcher = QFileSystemWatcher(page)
        self.timer = QTimer(page)  # a file is still being written when the folder first changes
        self.timer.setSingleShot(True)
        self.timer.setInterval(400)
        self.timer.timeout.connect(self.scan)
        self.watcher.directoryChanged.connect(lambda _: self.timer.start())
        # network folders and exhausted watch limits send no change signal: a slow scan covers them
        self.poll = QTimer(page)
        self.poll.setInterval(2000)
        self.poll.timeout.connect(self.scan)

    def start(self, folder):
        self.stop()
        self.folder, self.seen = str(folder), set(fits_in(folder))
        self.watcher.addPath(self.folder)
        self.poll.start()

    def stop(self):
        if self.folder:
            self.watcher.removePath(self.folder)
        self.poll.stop()
        self.folder = None

    def scan(self):
        if not self.folder:
            return
        try:
            new = [p for p in fits_in(self.folder) if p not in self.seen]
        except OSError:  # the folder went away
            return self.stop()
        self.seen.update(new)
        if new:
            (self.on_new or self.page.add_open)(new)


def strip_buttons(page, parent):
    """The two buttons above the list: Thumbnails and Follow a folder… (both checkable; off stops following)."""
    row = QWidget(parent)
    lay = QHBoxLayout(row)
    lay.setContentsMargins(0, 0, 0, 0)
    thumbs = QPushButton(translate("ImageWindow", "Thumbnails"), row)
    thumbs.setCheckable(True)
    thumbs.setToolTip(translate("ImageWindow", "Show the open images as thumbnails or as a list"))
    thumbs.toggled.connect(lambda on: set_thumbnails(page.open_list, on))
    follow = QPushButton(translate("ImageWindow", "Follow a folder…"), row)
    follow.setCheckable(True)
    follow.setToolTip(translate("ImageWindow", "New FITS files that appear in a folder are added to the open images"))
    follower = FolderFollower(page)

    def toggled(on):
        if not on:
            return follower.stop()
        folder = QFileDialog.getExistingDirectory(page, translate("ImageWindow", "Follow a folder…"))
        if folder:
            follower.start(folder)
        else:
            follow.setChecked(False)

    follow.toggled.connect(toggled)
    page.thumbs_button, page.follow_button, page.follower = thumbs, follow, follower
    lay.addWidget(thumbs)
    lay.addWidget(follow)
    return row
