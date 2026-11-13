"""The Photometry window's Field stage (plans/interface.md UI-16.1, plans/photometry.md PHO-25 item 4): identify the
field (the first frame solved against Gaia, the variables of VSX / GCVS named, the files' OBJECT checked), its
answer and the variable-star list, and what is drawn over the first frame: the variables, the Gaia stars, the AAVSO
sequence."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("PhotometryField", "…") calls


def field_stage(page):
    """The stage's widget; the page's field widgets (answer, variable list) and buttons move into it."""
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    intro = QLabel(translate("PhotometryField", "The first frame solved against Gaia: the known variable stars are "
                             "named and the files' OBJECT is checked. Needs the pointing and the pixel scale in the "
                             "header and the internet once."), w)  # fmt: skip
    intro.setWordWrap(True)
    lay.addWidget(intro)
    row = QHBoxLayout()
    for b in (page.identify_button, page.sequence_button):
        row.addWidget(b)
    lay.addLayout(row)
    lay.addWidget(page.field_label)
    row = QHBoxLayout()
    row.addWidget(page.variables, 1)
    row.addWidget(page.make_target)
    lay.addLayout(row)
    lay.addWidget(QLabel(f"<b>{translate('PhotometryField', 'Drawn on the first frame')}</b>", w))
    page.show_variables = QCheckBox(translate("PhotometryField", "Variable stars (VSX, GCVS)"), w)
    page.show_variables.setChecked(True)
    page.show_gaia = QCheckBox(translate("PhotometryField", "Gaia stars of the solution"), w)
    page.show_gaia.setToolTip(translate("PhotometryField", "The stars the field was solved with: a ring off its star "
                                        "means the solution is off there"))  # fmt: skip
    for box in (page.show_variables, page.show_gaia):
        box.toggled.connect(lambda _on: page._draw_markers())
        lay.addWidget(box)
    lay.addStretch(1)
    page.field_marks = lambda: gaia_marks(page)
    page.variables_on = page.show_variables.isChecked
    return w


def gaia_marks(page, limit=300):
    """Small grey rings at the solution's Gaia stars (the brightest `limit`), on the first frame only."""
    box = getattr(page, "show_gaia", None)
    stars = (page.field or {}).get("stars") if page.field else None
    if box is None or not box.isChecked() or not stars or page.shown != 0:
        return []
    order = sorted(range(len(stars["x"])), key=lambda i: stars["gmag"][i])[:limit]
    r = max(page.r_ap.value(), 3.0)
    from .kit.tokens import role

    return [(stars["x"][i], stars["y"][i], r, role("rejected"), "", "dash", "quiet") for i in order]
