"""Extra Images-window pieces on the anatomy (UI-16.10): the empty state, the Levels / Layers / History inspector tabs
and the file strip's filter line. They reuse the dialog and the undo stack; the dialogs and menus stay."""

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QUndoView,
    QVBoxLayout,
    QWidget,
)

from .image_follow import strip_buttons

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("ImageWindow", "…") calls


class LayersList(QListWidget):
    """One check box per overlay drawn on the image (the Overlays > Layers menu, as a list)."""

    def __init__(self, viewer, parent=None):
        super().__init__(parent)
        self.viewer = viewer
        self.itemChanged.connect(lambda i: viewer.set_layer(i.text(), visible=i.checkState() == Qt.Checked))

    def refresh(self):
        self.blockSignals(True)
        self.clear()
        for name in self.viewer.overlay_names():
            item = QListWidgetItem(name, self)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if self.viewer.layer_visible(name) else Qt.Unchecked)
        if not self.count():
            self.addItem(translate("ImageWindow", "No overlays on this image"))
            self.item(0).setFlags(Qt.NoItemFlags)
        self.blockSignals(False)


def add_inspector_tabs(page):
    """Levels, Layers and History beside Header / Information / Graph; they refresh when shown."""
    from .levels_dialog import LevelsDialog

    levels = LevelsDialog(page.viewer, page)
    levels.setWindowFlags(Qt.Widget)  # a dialog class used as a panel
    layers = LayersList(page.viewer, page)
    history = QUndoView(page.undo_stack, page)
    page.levels_panel, page.layers_panel, page.history_panel = levels, layers, history
    page.tabs.addTab(levels, translate("ImageWindow", "Levels"))
    page.tabs.addTab(layers, translate("ImageWindow", "Layers"))
    page.tabs.addTab(history, translate("ImageWindow", "History"))

    def refresh(_=None):
        if page.tabs.currentWidget() is levels:
            levels.cmap.setCurrentIndex(levels.cmap.findData(page.viewer.cmap))
            levels.invert.setChecked(page.viewer.invert)
            levels.refresh()
        elif page.tabs.currentWidget() is layers:
            layers.refresh()

    page.tabs.currentChanged.connect(refresh)
    page.refresh_inspector = refresh


def file_strip(page):
    """The open-images list with a filter line above it; several files can be selected."""
    page.open_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
    box = QWidget(page)
    lay = QVBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    line = QLineEdit(box)
    line.setClearButtonEnabled(True)
    line.setPlaceholderText(translate("ImageWindow", "Filter by name"))
    line.setToolTip(translate("ImageWindow", "Shows only the open images whose name contains this text"))

    def apply(text):
        for i in range(page.open_list.count()):
            item = page.open_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    line.textChanged.connect(apply)
    page.filter_line = line
    lay.addWidget(line)
    lay.addWidget(strip_buttons(page, box))
    lay.addWidget(page.open_list, 1)
    page.selected_paths = lambda: [i.data(Qt.UserRole) for i in page.open_list.selectedItems()]
    return box


def empty_state(main):
    from .kit.empty import EmptyState

    return EmptyState(
        "open",
        translate("ImageWindow", "No images yet"),
        translate("ImageWindow", "Open FITS files to look at them, measure stars and read their headers."),
        (translate("ImageWindow", "Open images…"), lambda: main.open_fits_dialog()),
        (translate("ImageWindow", "Open the practice night"), lambda: main.practice_data()),
    )
