"""What the Photometry window chose by itself, listed in the stage where it was chosen with its reason
(plans/photometry.md PHO-W: the target from the files' OBJECT, the comparison stars, the radii). The texts are
the ones the page already shows in its result line; here they stay in their stage."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QLabel

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("PhotometryChoices", "…") calls


def attach(win, page):
    """Wrap the page's three automatic steps so that each leaves its choice and reason in its stage."""
    from .photometry_catalog_choice import attach as catalogue_choice

    catalogue_choice(win, win.parent(), page)  # PHO-25 item 3: the magnitude source and its stars
    from .photometry_dia import attach as difference_imaging

    difference_imaging(win, page)  # PHO-29: the crowded-field action, its result tab
    labels = {}

    def note(stage, text):
        label = labels.get(stage)
        if label is None:
            label = labels[stage] = QLabel(win.stage_panels[stage])
            label.setObjectName("automatic_choices")
            label.setWordWrap(True)
            label.setProperty("muted", True)
            win.stage_panels[stage].add(label)
        head = translate("PhotometryChoices", "Chosen automatically")
        label.setText(f"<b>{head}</b><br>{text.replace(chr(10), '<br>')}")

    target, comps, radii = page._set_target_from_field, page.set_comparisons, page.show_apertures

    def from_field(xy, v):
        target(xy, v)
        note("field", translate("PhotometryChoices", "Target: {name}, the star the files' OBJECT names; its "
                               "catalogue position gives the barycentric times.").format(name=v["name"]))  # fmt: skip

    def with_comps(found, catalogue=None):
        comps(found, catalogue)
        note("stars", page.result.text())

    def with_radii(a):
        radii(a)
        note("apertures", page.result.text())

    page._set_target_from_field, page.set_comparisons, page.show_apertures = from_field, with_comps, with_radii
