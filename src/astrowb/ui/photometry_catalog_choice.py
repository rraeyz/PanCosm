"""Which catalogue the comparison magnitudes come from, in the Photometry window's Stars stage (plans/photometry.md
PHO-25 item 3): the choice is remembered, steers the page's magnitude source, and "Show catalogue stars" draws that
catalogue's stars on the first frame (one cone on the ESA Gaia archive's copies, looked up off the window's thread;
the AAVSO sequence uses its own look-up). Every failure is said in the stage, none raises."""

import threading

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QWidget

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("PhotometryCatalogue", "…") calls

KEY = "photometry.catalogue_source"
# key: (page.mag_source value or None, table, ra, dec, magnitude column, band shown); the others are drawn only
SOURCES = {
    "gspc": ("auto", "gaiadr3.gaia_source AS g JOIN gaiadr3.synthetic_photometry_gspc AS s "
             "ON s.source_id = g.source_id", "g.ra", "g.dec", "s.v_jkc_mag", "V"),
    "apass": ("apass", "external.apassdr9", "raj2000", "dej2000", "vmag", "V"),
    "ps1": (None, "gaiadr2.panstarrs1_original_valid", "ra", "dec", "r_mean_psf_mag", "r"),
    "skymapper": (None, "external.skymapperdr2_master", "raj2000", "dej2000", "r_psf", "r"),
    "aavso": ("aavso", None, None, None, None, None),
}  # fmt: skip


def names():
    return {
        "gspc": translate("PhotometryCatalogue", "Gaia GSPC"),
        "apass": translate("PhotometryCatalogue", "APASS DR9"),
        "ps1": translate("PhotometryCatalogue", "Pan-STARRS1 DR1"),
        "skymapper": translate("PhotometryCatalogue", "SkyMapper DR2 (south)"),
        "aavso": translate("PhotometryCatalogue", "AAVSO sequence"),
    }


def field_stars(source, ra, dec, radius_deg, limit=300):
    """The brightest `limit` stars of one catalogue in a cone: [{ra, dec, mag}], cached by the Gaia archive client."""
    from ..gaia import _run

    _, table, ra_col, dec_col, mag, _band = SOURCES[source]
    t = _run(
        f"SELECT TOP {int(limit)} {ra_col} AS ra, {dec_col} AS dec, {mag} AS mag FROM {table} WHERE "
        f"1=CONTAINS(POINT('ICRS', {ra_col}, {dec_col}), CIRCLE('ICRS', {float(ra)}, {float(dec)}, "
        f"{float(radius_deg)})) AND {mag} IS NOT NULL ORDER BY {mag}"
    )
    return [{"ra": float(r["ra"]), "dec": float(r["dec"]), "mag": float(r["mag"])} for r in t]


def attach(win, main, page):
    panel = win.stage_panels["stars"]
    box = QWidget(panel)
    row = QHBoxLayout(box)
    row.setContentsMargins(0, 0, 0, 0)
    page.catalogue_choice = combo = QComboBox(box)
    for key, name in names().items():
        combo.addItem(name, key)
    combo.setToolTip(translate("PhotometryCatalogue", "The catalogue the comparison magnitudes are taken from and "
                               "drawn from; Pan-STARRS1 and SkyMapper are only drawn"))  # fmt: skip
    saved = combo.findData(main.settings.get(KEY))
    combo.setCurrentIndex(max(saved, 0))
    page.catalogue_button = button = QPushButton(translate("PhotometryCatalogue", "Show catalogue stars"), box)
    button.setToolTip(translate("PhotometryCatalogue", "Draws the chosen catalogue's stars on the first frame"))
    page.catalogue_note = note = QLabel(panel)
    note.setWordWrap(True)
    note.setProperty("muted", True)
    row.addWidget(combo, 1)
    row.addWidget(button)
    panel.add(QLabel(f"<b>{translate('PhotometryCatalogue', 'Comparison magnitudes from')}</b>", panel))
    panel.add(box)
    panel.add(note)
    combo.currentIndexChanged.connect(lambda _i: choose(main.settings, page))
    button.clicked.connect(lambda: show(page))


def choose(settings, page):
    """Remember the choice; the page's magnitude source follows where the catalogue is one of its own."""
    key = page.catalogue_choice.currentData()
    settings.set(KEY, key)
    source = SOURCES[key][0]
    if source is not None:
        page.mag_source.setCurrentIndex(page.mag_source.findData(source))


def show(page):
    import numpy as np

    from .kit.handoff import to_main
    from .photometry_stars import show_sequence

    key = page.catalogue_choice.currentData()
    page.viewer.set_items("catalogue", [])
    if not page.field or page.viewer.data is None:
        page.catalogue_note.setText(translate("PhotometryCatalogue", "Identify the field first: the stars are placed "
                                              "by its plate solution."))  # fmt: skip
        return
    if key == "aavso":
        return show_sequence(page)
    if page.shown != 0:
        page.show_frame(0)  # the solution belongs to the first frame
    wcs, (ny, nx) = page._field_wcs(), page.viewer.data.shape
    ra, dec = wcs.pixel_to_world_values(np.array([(nx - 1) / 2, 0.0]), np.array([(ny - 1) / 2, 0.0]))
    radius = float(np.hypot((ra[1] - ra[0]) * np.cos(np.radians(dec[0])), dec[1] - dec[0]) * 1.05)
    page.catalogue_note.setText(translate("PhotometryCatalogue", "Looking up {name}…").format(name=names()[key]))
    arrive = to_main(page, lambda answer: draw(page, wcs, key, answer))

    def work():
        try:
            answer = field_stars(key, float(ra[0]), float(dec[0]), radius)
        except Exception as e:  # noqa: BLE001 - the network, the cache or the archive: said in the stage
            answer = e
        arrive(answer)

    threading.Thread(target=work, daemon=True).start()


def draw(page, wcs, key, answer):
    from .. import overlays
    from .image.layers import Circle
    from .kit.tokens import role
    from .messages import translate as message

    if isinstance(answer, Exception):
        page.catalogue_note.setText(message(answer))
        return
    inside = overlays.to_pixels(wcs, page.viewer.data.shape, answer)
    page.viewer.set_items("catalogue", [Circle(colour=role("check"), x=s["x"], y=s["y"], r=9, label=f"{s['mag']:.2f}")
                                        for s in inside])  # fmt: skip
    text = translate("PhotometryCatalogue", "{name}: {n} star(s) on the frame, labelled with {band} magnitudes.")
    page.catalogue_note.setText(text.format(name=names()[key], n=len(inside), band=SOURCES[key][5]))
    if not inside:
        page.catalogue_note.setText(translate("PhotometryCatalogue", "{name} has no star on the frame.").format(
            name=names()[key]))  # fmt: skip
