"""TESS cut-outs in the Photometry window's Images stage (PHO-32): a target name or TIC number, the cut-out size, and a
button that runs photometry.tesscut (MAST TESScut, the only network use here) and opens the pixel files it gives as
if the user had chosen them. Every failure is said in the stage's status line, none raises."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QSpinBox, QWidget

from .kit.buttons import Button

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("PhotometryTess", "…") calls


def attach(win, page):
    row = QWidget(win.stage_panels["images"])
    page.tess_target = QLineEdit(row)
    page.tess_target.setPlaceholderText(translate("PhotometryTess", "TESS target (name or TIC)"))
    page.tess_size = QSpinBox(row)
    page.tess_size.setRange(1, 99)
    page.tess_size.setValue(15)
    page.tess_size.setSuffix(" px")
    page.tess_size.setToolTip(translate("PhotometryTess", "Side of the square cut out of the full-frame images"))
    page.tess_button = Button(translate("PhotometryTess", "Get TESS cut-outs"), "normal", parent=row)
    page.tess_button.setToolTip(
        translate("PhotometryTess", "Downloads TESS full-frame-image cut-outs of the target from MAST, one pixel "
                  "file per sector, and opens them as the frames"))  # fmt: skip
    lay = QHBoxLayout(row)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.addWidget(page.tess_target, 1)
    lay.addWidget(page.tess_size)
    lay.addWidget(page.tess_button)
    page.tess_button.clicked.connect(lambda: start(win.parent(), page))
    page.tess_target.returnPressed.connect(page.tess_button.click)
    win.stage_panels["images"].add(row)


def start(main, page):
    from ..services.cache import folder

    target = page.tess_target.text().strip()
    if not target:
        return
    if target.isdigit():  # a bare number is a TIC number; MAST resolves "TIC n"
        target = f"TIC {target}"
    page.tess_button.setEnabled(False)
    page.images_label.setText(translate("PhotometryTess", "Fetching TESS cut-outs of {name}…").format(name=target))
    main.run_step_for(
        "photometry",
        "photometry.tesscut",
        {"target": target, "cache": str(folder() / "tesscut")},
        {"size": page.tess_size.value()},
        on_done=lambda out: done(page, out),
        on_fail=lambda message: fail(page, message),
    )


def done(page, out):
    page.tess_button.setEnabled(True)
    page.set_images(out["images"])


def fail(page, message):
    from .messages import translate as message_text

    page.tess_button.setEnabled(True)
    page.images_label.setText(message_text(message))
