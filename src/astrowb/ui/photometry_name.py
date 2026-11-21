"""Target by name in the Photometry window's Field stage: the name is looked up (kit ObjectField: planning.resolve,
SIMBAD with a local cache, so a name seen before works offline), put on the first frame through the field's plate
solution and the star there becomes the target. Every failure is said in the stage, none raises."""

from PySide6.QtCore import QCoreApplication

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("PhotometryName", "…") calls


def attach(win, main, page):
    from ..settings import config_dir
    from .kit.object_field import ObjectField

    panel = win.stage_panels["field"]
    field = ObjectField(main.run_step, lambda: config_dir() / "targets.json", parent=panel)
    field.edit.setPlaceholderText(translate("PhotometryName", "Target by name, e.g. NY Vir"))
    field.button.setText(translate("PhotometryName", "Find target"))
    field.button.setToolTip(
        translate("PhotometryName", "Looks the name up (SIMBAD; a name seen before works offline) and takes the star "
                  "at its position on the solved first frame as the target"))  # fmt: skip
    page.target_name, page.name_button, page.name_answer = field.edit, field.button, field.answer
    # the position on the image needs the plate solution
    field.precheck = lambda: (
        None
        if page.field
        else translate(
            "PhotometryName", "Identify the field first: the name is placed on the image through its plate solution."
        )
    )
    field.resolved.connect(lambda name, target: place(page, name, target))
    panel.add(field)


def fail(page, message):
    from .messages import translate as message_text

    page.name_answer.setText(message_text(message))


def place(page, name, target):
    """The resolved target on the first frame: the nearest star within a few pixels is the target."""
    from .photometry_stars import snap_click

    try:
        data = page.viewer.data
        x, y = (float(v) for v in page._field_wcs().world_to_pixel_values(target["ra"], target["dec"]))
        if data is None or not (0 <= x < data.shape[1] and 0 <= y < data.shape[0]):
            raise ValueError
    except (ValueError, TypeError, AttributeError):
        page.name_answer.setText(translate("PhotometryName", "{name} is not on this field.").format(name=name))
        return
    if page.shown != 0:
        page.show_frame(0)  # the solution belongs to the first frame
    x, y = snap_click(page, x, y)
    page.name_answer.setText(
        translate("PhotometryName", "{name}: RA {ra:.4f}°, Dec {dec:+.4f}° → pixel {x:.1f}, {y:.1f}.").format(
            name=name, ra=target["ra"], dec=target["dec"], x=x + 1, y=y + 1
        )
    )
    v = {"name": name, "ra": target["ra"], "dec": target["dec"], "x": x, "y": y}
    page.edit(translate("PhotometryName", "target by name"), page._set_target_from_field, (x, y), v)
