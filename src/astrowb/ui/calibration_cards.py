"""UI-16.2: the Continue stage's cards: what to do next with the calibrated frames. A card is the page's own button
(Photometry, Stack) or a hand-over signal (Images) in a card; enabled after a result, like the buttons."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

translate = QCoreApplication.translate


def make(page):
    """The cards' widget (page.continue_cards: {key: button}); the page's Photometry and Stack buttons stay as the
    cards' targets, hidden. Cards follow the page's result by wrapping show_result."""
    box = QWidget()
    lay = QVBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    cards = (
        ("photometry", translate("CalibrationWindow", "Measure in Photometry"),
         translate("CalibrationWindow", "Sends the calibrated lights to Photometry: a light curve, a variable star."),
         page.photometry_button.click),
        ("stack", translate("CalibrationWindow", "Stack"),
         translate("CalibrationWindow", "Aligns the calibrated images and adds them into one deep picture per filter."),
         page.stack_button.click),
        ("images", translate("CalibrationWindow", "Open in Images"),
         translate("CalibrationWindow", "Shows the calibrated images in the Images window to look at or process."),
         lambda: page.images_requested.emit(list(page.calibrated))),
    )  # fmt: skip
    page.continue_cards = {}
    for key, title, text, action in cards:
        button = QPushButton(title, box)
        button.setToolTip(text)
        button.setEnabled(False)
        button.clicked.connect(lambda _=False, a=action: a())
        label = QLabel(text, box)
        label.setWordWrap(True)
        lay.addWidget(button)
        lay.addWidget(label)
        page.continue_cards[key] = button
        setattr(page, f"{key}_card", button)  # a name for the guided tasks and the walks
    for old in (page.photometry_button, page.stack_button):
        old.hide()  # the cards press them: same hand-over, same state

    show = page.show_result

    def show_result(out):
        show(out)
        for key, old in (("photometry", page.photometry_button), ("stack", page.stack_button)):
            page.continue_cards[key].setEnabled(old.isEnabled())
        page.continue_cards["images"].setEnabled(bool(page.calibrated))

    page.show_result = show_result
    return box
