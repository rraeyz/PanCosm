"""The comparison stars' side of the Photometry window (plans/photometry.md PHO-17): the sentence after a suggestion
and the "Why these stars?" table — every catalogue star with the rule that left it out (photometry.comprules),
sortable, a row's star shown on the image when chosen."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QPushButton

from .kit.dialogs import Dialog
from .kit.table_view import DataTable

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("PhotometryStars", "…") calls


def verdicts():
    return {
        "chosen": translate("PhotometryStars", "chosen"),
        "not_needed": translate("PhotometryStars", "passed (enough stars already)"),
        "too_bright": translate("PhotometryStars", "too bright"),
        "too_faint": translate("PhotometryStars", "too faint"),
        "catalogue_error": translate("PhotometryStars", "catalogue error too large"),
        "variable_vsx": translate("PhotometryStars", "variable (VSX)"),
        "variable_gcvs": translate("PhotometryStars", "variable (GCVS)"),
        "variable_gaia": translate("PhotometryStars", "variable (Gaia)"),
        "noisy_gaia": translate("PhotometryStars", "scatter in Gaia (likely variable)"),
        "too_far": translate("PhotometryStars", "too far from the target"),
        "edge": translate("PhotometryStars", "too near the edge"),
        "neighbour": translate("PhotometryStars", "a neighbour in its aperture or sky ring"),
        "saturated": translate("PhotometryStars", "saturated on some frame"),
        "non_linear": translate("PhotometryStars", "beyond the linear range"),
        "low_snr": translate("PhotometryStars", "signal-to-noise too low"),
        "colour": translate("PhotometryStars", "colour too different"),
    }


def suggestion_text(n, catalogue):
    """The sentence shown after a suggestion from Gaia."""
    text = translate(
        "PhotometryStars",
        "{n} comparison stars chosen from Gaia: about as bright as the target, not variable, alone, unsaturated, "
        "inside every frame.",
    ).format(n=n)
    if not catalogue.get("same_colour"):
        text += " " + translate(
            "PhotometryStars",
            "No star of the target's colour (BP−RP {c:.2f}) is in the field: with stars of another colour the light "
            "curve can drift slowly with airmass; detrend it against airmass.",
        ).format(c=catalogue["colour"])
    if catalogue.get("table"):
        text += " " + translate(
            "PhotometryStars", "“Why these stars?” shows every star with the reason it was left out."
        )
    return text


def why_dialog(page, table, show_star=None):
    """The table of every judged star; choosing a row calls show_star((x, y))."""
    d = Dialog(translate("PhotometryStars", "Why these stars?"), page, getattr(page, "settings", None), "why_stars")
    view = DataTable(d)
    names = verdicts()
    header = [
        translate("PhotometryStars", "Verdict"),
        translate("PhotometryStars", "Magnitude (G)"),
        translate("PhotometryStars", "BP−RP"),
        translate("PhotometryStars", "Distance (px)"),
        translate("PhotometryStars", "Peak"),
        translate("PhotometryStars", "S/N"),
        "x",
        "y",
    ]
    rows = [[names.get(r["verdict"], r["verdict"]), round(r["mag"], 2), round(r["colour"], 2), round(r["distance"]),
             round(r["peak"]), round(r["snr"]), round(r["x"], 1), round(r["y"], 1)] for r in table]  # fmt: skip
    view.set_data(header, rows, keys=[(r["x"], r["y"]) for r in table])
    if show_star is not None:
        view.row_chosen.connect(lambda key: key is not None and show_star(key))
    d.body.addWidget(view)
    close = d.add_buttons(translate("PhotometryStars", "Close"))
    close.setDefault(True)
    d.resize(max(d.width(), 760), max(d.height(), 480))
    return d


def add_star_buttons(page, layout):
    """ "Suggest comparison stars" and "Why these stars?" under the star list."""
    page.suggest_button = QPushButton(translate("PhotometryStars", "Suggest comparison stars"), page)
    page.suggest_button.setEnabled(False)
    page.suggest_button.setToolTip(
        translate(
            "PhotometryStars", "Similar brightness, not saturated, no bright neighbour, inside the frame in every image"
        )
    )
    page.suggest_button.clicked.connect(lambda: page._suggest(auto=False))
    page.why_button = QPushButton(translate("PhotometryStars", "Why these stars?"), page)
    page.why_button.setEnabled(False)
    page.why_button.setToolTip(
        translate("PhotometryStars", "Every catalogue star near the target's brightness, with its reason")
    )
    page.why_button.clicked.connect(
        lambda: why_dialog(page, page.judged_stars, lambda xy: page.viewer.centerOn(*xy)).open()
    )
    layout.addWidget(page.suggest_button)
    layout.addWidget(page.why_button)


def snap_click(page, x, y):
    """A click on the image moved onto the star it was meant for (photometry.aperture.snap_to_star): within three
    screen pixels, at least 4 image pixels (on a frame shown smaller than its pixels a click lands pixels off)."""
    from ..photometry.aperture import snap_to_star

    data = page.viewer.data
    if data is None or data.ndim != 2:
        return x, y
    scale = abs(page.viewer.transform().m11()) or 1.0  # screen pixels per image pixel
    sx, sy = snap_to_star(data, [(x, y)], radius=max(4.0, 3.0 / scale))[0]
    return float(sx), float(sy)
