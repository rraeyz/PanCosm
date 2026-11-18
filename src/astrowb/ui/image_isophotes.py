"""PHO-39: Images → Analyse → "Isophotes and surface brightness…" (the step `photometry.isophotes`, its profile in a
result tab) and "Sky brightness…" (`compute.isophote.sky_brightness`). The zero point (header MAGZP) and the pixel
scale (the WCS) are offered when the image has them; nothing is guessed, a missing one is asked for or named."""

from astropy.table import Table
from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QMessageBox

from .image_sources import find_action
from .kit.table import TableView

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("ImageWindow", "…") calls


def _number(text):
    """A float from a field, None when it is empty; ValueError when it is not a number."""
    text = text.strip()
    return float(text) if text else None


def known_calibration(page):
    """(zero point, pixel scale in ″/px) from the image's own header and WCS; None for what it does not say."""
    from ..hdr import get

    return get(page.header or {}, "MAGZP", "PHOTZP"), page._scale()


def sky_text(page, zero_point, scale):
    """The frame's sky as a sentence in mag/arcsec²; ValueError naming what is missing."""
    from ..compute.isophote import sky_brightness

    missing = [n for n, v in ((translate("ImageWindow", "zero point"), zero_point),
                              (translate("ImageWindow", "pixel scale"), scale)) if not v]  # fmt: skip
    if missing or page.viewer.data is None:
        raise ValueError(
            translate("ImageWindow", "Missing: %1.").replace(
                "%1", ", ".join(missing) or translate("ImageWindow", "image")
            )
        )
    sb = sky_brightness(page.viewer.data, zero_point, scale)
    return translate("ImageWindow", "Sky: %1 mag/arcsec²").replace("%1", f"{sb:.2f}")


def profile_table(profile):
    return Table({k: v for k, v in profile.items()})


def run_isophotes(win, page, x, y, zero_point=None, scale=None):
    """Run the step on the shown image round (x, y) (0-based); the profile lands in the Isophotes tab."""
    main, path = win.parent(), getattr(win.parent(), "current_path", None)
    if path is None or page.viewer.data is None:
        return None
    params = {"zero_point": zero_point, "pixel_scale": scale}

    def done(out):
        if getattr(page, "isophote_view", None) is None:
            page.isophote_view = TableView(win)
            page.isophote_view.view.setObjectName("isophote_table")
            win.add_result_tab("isophotes", translate("ImageWindow", "Isophotes"), page.isophote_view)
        page.isophotes = profile_table(out["isophotes"])
        page.isophote_view.set_table(page.isophotes)

    return main.run_step("photometry.isophotes", {"image": str(path), "target_xy": (x, y)}, params, on_done=done)


def _ask(win, page, with_target):
    """The dialog: target (x y) when with_target, zero point and pixel scale; values or None when cancelled."""
    h, w = page.viewer.data.shape
    zp, scale = known_calibration(page)
    click = getattr(page, "isophote_click", None) or ((w - 1) / 2, (h - 1) / 2)
    dlg = QDialog(win)
    form = QFormLayout(dlg)
    xy = QLineEdit(f"{click[0]:.1f} {click[1]:.1f}")
    fields = [QLineEdit("" if zp is None else f"{zp:g}"), QLineEdit("" if scale is None else f"{scale:g}")]
    if with_target:
        form.addRow(translate("ImageWindow", "Target x y (pixels, 0-based; last click)"), xy)
    form.addRow(translate("ImageWindow", "Zero point (mag)"), fields[0])
    form.addRow(translate("ImageWindow", "Pixel scale (″/px)"), fields[1])
    box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    box.accepted.connect(dlg.accept)
    box.rejected.connect(dlg.reject)
    form.addRow(box)
    if not dlg.exec():
        return None
    try:
        x, y = (float(v) for v in xy.text().replace(",", " ").split())
        return x, y, _number(fields[0].text()), _number(fields[1].text())
    except ValueError:
        QMessageBox.warning(win, translate("ImageWindow", "Isophotes"), translate("ImageWindow", "Not a number."))
        return None


def analyse_actions(win, page):
    """Find stars and the two extended-object Analyse actions; a click on the image is remembered as the target."""
    page.viewer.clicked.connect(lambda x, y: setattr(page, "isophote_click", (x, y)))
    iso = QAction(translate("ImageWindow", "Isophotes and surface brightness…"), win)
    iso.setToolTip(translate("ImageWindow", "Fit ellipses round the target and list the profile in the Isophotes tab"))
    sky = QAction(translate("ImageWindow", "Sky brightness…"), win)
    sky.setToolTip(
        translate("ImageWindow", "The sky of the shown image in mag/arcsec² (needs a zero point and a pixel scale)")
    )

    def on_iso():
        if page.viewer.data is not None and (a := _ask(win, page, True)):
            run_isophotes(win, page, *a)

    def on_sky():
        if page.viewer.data is None or not (a := _ask(win, page, False)):
            return
        try:
            QMessageBox.information(win, translate("ImageWindow", "Sky brightness"), sky_text(page, a[2], a[3]))
        except ValueError as e:
            QMessageBox.warning(win, translate("ImageWindow", "Sky brightness"), str(e))

    iso.triggered.connect(lambda _=False: on_iso())
    sky.triggered.connect(lambda _=False: on_sky())
    return [find_action(win, page), iso, sky]
