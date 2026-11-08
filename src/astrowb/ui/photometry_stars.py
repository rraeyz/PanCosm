"""The comparison stars' side of the Photometry window (plans/photometry.md PHO-17): the sentence after a suggestion
and the "Why these stars?" table — every catalogue star with the rule that left it out (photometry.comprules),
sortable, a row's star shown on the image when chosen."""

from PySide6.QtCore import QCoreApplication, QObject, Signal
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
    use = d.use_button = QPushButton(translate("PhotometryStars", "Use this star anyway"), d)
    use.setToolTip(translate("PhotometryStars", "The chosen star becomes a comparison star, whatever its verdict"))
    use.setEnabled(False)
    chosen = []

    def choose(key):
        chosen[:] = [key] if key is not None else []
        use.setEnabled(key is not None and tuple(key) not in {tuple(c) for c in page.comps})

    def use_it():
        if chosen:
            page.edit(
                translate("PhotometryStars", "use a star anyway"), page._set_comps, [*page.comps, tuple(chosen[0])]
            )
            use.setEnabled(False)

    view.row_chosen.connect(choose)
    use.clicked.connect(use_it)
    d.button_row.addWidget(use)
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
    page.identify_button = QPushButton(translate("PhotometryStars", "Identify the field"), page)
    page.identify_button.setToolTip(
        translate("PhotometryStars", "Plate solution of the first frame, its Gaia stars and the VSX variables in it")
    )
    page.identify_button.clicked.connect(lambda: identify_field(page))
    page.sequence_button = QPushButton(translate("PhotometryStars", "Show the AAVSO sequence"), page)
    page.sequence_button.setToolTip(
        translate("PhotometryStars", "The AAVSO chart's comparison stars on the first frame, with their labels")
    )
    page.sequence_button.clicked.connect(lambda: show_sequence(page))
    page.rules_button = QPushButton(translate("PhotometryStars", "Rules for comparison stars…"), page)
    page.rules_button.setToolTip(
        translate(
            "PhotometryStars", "Brightness and colour window, distance, variables, S/N, how many: Suggest uses them"
        )
    )
    page.rules_button.clicked.connect(lambda: _edit_rules(page))
    for w in (page.suggest_button, page.rules_button, page.why_button, page.identify_button, page.sequence_button):
        layout.addWidget(w)


def _edit_rules(page):
    from .comparison_rules import RulesDialog

    page.rules_dialog = RulesDialog(None, page)
    page.rules_dialog.open()


class _Relay(QObject):
    done = Signal(object)


def show_sequence(page):
    """The field's AAVSO sequence (services.aavso_vsp) drawn on the first frame, looked up off the window's thread
    (the first look-up goes to the internet; later ones come from the cache)."""
    import threading

    import numpy as np

    from ..services import aavso_vsp

    if not page.field or page.viewer.data is None:
        page.field_label.setText(
            translate("PhotometryStars", "Identify the field first: the sequence is placed by it.")
        )
        page.field_label.show()
        return
    if page.shown != 0:
        page.show_frame(0)  # the solution belongs to the first frame
    wcs, (ny, nx) = page._field_wcs(), page.viewer.data.shape
    ra, dec = wcs.pixel_to_world_values(np.array([(nx - 1) / 2, 0.0]), np.array([(ny - 1) / 2, 0.0]))
    fov = 2 * 60 * np.hypot((ra[1] - ra[0]) * np.cos(np.radians(dec[0])), dec[1] - dec[0]) * 1.05
    page.field_label.setText(translate("PhotometryStars", "Looking up the AAVSO sequence…"))
    page.sequence_relay = relay = _Relay(page)
    relay.done.connect(lambda answer: _draw_sequence(page, wcs, answer))

    def work():
        try:
            answer = aavso_vsp.sequence(float(ra[0]), float(dec[0]), fov=float(fov), maglimit=17.0)
        except Exception as e:  # noqa: BLE001 - the network, the cache or VSP: said on the page
            answer = e
        try:
            relay.done.emit(answer)
        except RuntimeError:  # the page was closed meanwhile
            pass

    threading.Thread(target=work, daemon=True).start()


def _draw_sequence(page, wcs, answer):
    from .. import overlays
    from .kit.tokens import DARK
    from .messages import translate as message

    if isinstance(answer, Exception):
        page.field_label.setText(message(answer))
        return
    stars = [{"name": s["label"], "ra": s["ra"], "dec": s["dec"], "mag": None} for s in answer["stars"]]
    inside = overlays.to_pixels(wcs, page.viewer.data.shape, stars)
    page.viewer.set_overlay("aavso", DARK["ok"], circles=[(s["x"], s["y"], 9, s["name"]) for s in inside])
    page.field_label.setText(
        translate(
            "PhotometryStars", "AAVSO chart {chart}: {n} sequence star(s) on the frame (green, labelled)."
        ).format(chart=answer["chart"], n=len(inside))
    )


def identify_field(page, automatic=False):
    """The first frame solved and its stars named (photometry.identify_field); when the frames are opened only if
    Settings → Automatic steps allows it (ui/automatic.py)."""
    from . import automatic as steps

    if not page.images:
        return
    if automatic and not steps.on("photometry.identify_field"):
        page.field_label.setText(
            translate("PhotometryStars", "The field is identified when you press Identify the field.")
        )
        page.field_label.show()
        return
    if not automatic and page.field:  # pressed again on an identified field: no saved answers (user-feedback UF-14)
        page.identify_fresh = True
    page.field_label.setText(translate("PhotometryPage", "Identifying the field (Gaia, VSX)…"))
    page.field_label.show()
    page.field_requested.emit(page.images[0])


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
