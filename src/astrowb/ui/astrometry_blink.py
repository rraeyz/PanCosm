"""UI-16.11: blink the Astrometry window's frames in the existing blink window."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QPushButton

translate = QCoreApplication.translate


def blink_button(page):
    """A button for the Find stage; enabled while the page holds two or more frames."""
    b = QPushButton(translate("MovingObjectPage", "Blink the frames…"), page)
    b.setEnabled(False)
    b.clicked.connect(lambda: open_blink(page))
    b.setToolTip(
        translate("MovingObjectPage", "Shows the frames one after the other, aligned on the stars: a mover jumps out")
    )
    return b


def open_blink(page):
    from .blink_dialog import BlinkDialog

    dlg = BlinkDialog(page)
    dlg.set_images(page.images)  # time order and the star alignment are the blink window's own
    dlg.show()
    page.blink = dlg
    return dlg
