"""The quick commands of the Observing window: Park, Abort, Resume, Autofocus (placed by their stages)."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QPushButton

translate = QCoreApplication.translate


def quick_buttons(page):
    for text, path, tip in (
        (
            translate("ObservePage", "Park"),
            "/park",
            translate("ObservePage", "Stops any slew and sends the mount to its park position"),
        ),
        (
            translate("ObservePage", "Abort"),
            "/abort",
            translate("ObservePage", "Stops the running sequence, exposure or slew at once; the mount is not parked"),
        ),
        (
            translate("ObservePage", "Resume"),
            "/resume",
            translate(
                "ObservePage", "After a safety stop: allows sequences again, refused while anything is still unsafe"
            ),
        ),
        (
            translate("ObservePage", "Autofocus"),
            "/autofocus",
            translate(
                "ObservePage",
                "Frames at nine focuser positions around the present one; the star size (HFR) against "
                "position is fitted and the focuser moved to the best",
            ),
        ),
    ):
        b = QPushButton(text, page)
        b.setToolTip(tip)
        b.clicked.connect(lambda _=False, p=path: page._post(p))
        page.buttons[path.strip("/")] = b
