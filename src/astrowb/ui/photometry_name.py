"""Target by name in the Photometry window's Field stage: the name is looked up (planning.resolve: SIMBAD with a
local cache, so a name seen before works offline), put on the first frame through the field's plate solution and
the star there becomes the target. Every failure is said in the stage, none raises."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QWidget

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("PhotometryName", "…") calls


def attach(win, main, page):
    panel = win.stage_panels["field"]
    row = QWidget(panel)
    lay = QHBoxLayout(row)
    lay.setContentsMargins(0, 0, 0, 0)
    page.target_name = QLineEdit(row)
    page.target_name.setPlaceholderText(translate("PhotometryName", "Target by name, e.g. NY Vir"))
    page.name_button = QPushButton(translate("PhotometryName", "Find target"), row)
    page.name_button.setToolTip(
        translate("PhotometryName", "Looks the name up (SIMBAD; a name seen before works offline) and takes the star "
                  "at its position on the solved first frame as the target"))  # fmt: skip
    lay.addWidget(page.target_name, 1)
    lay.addWidget(page.name_button)
    page.name_answer = QLabel(row)
    page.name_answer.setWordWrap(True)
    page.name_answer.setProperty("muted", True)
    panel.add(row)
    panel.add(page.name_answer)
    page.name_button.clicked.connect(lambda: find(main, page))
    page.target_name.returnPressed.connect(page.name_button.click)


def find(main, page):
    from ..settings import config_dir

    name = page.target_name.text().strip()
    if not name:
        return
    if not page.field:  # the position on the image needs the plate solution
        page.name_answer.setText(translate("PhotometryName", "Identify the field first: the name is placed on the "
                                           "image through its plate solution."))  # fmt: skip
        return
    page.name_answer.setText(translate("PhotometryName", "Looking up {name}…").format(name=name))
    main.run_step(
        "planning.resolve",
        {"name": name, "cache_file": str(config_dir() / "targets.json")},
        on_done=lambda out: place(page, name, out["target"]),
        on_fail=lambda message: fail(page, message),
    )


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
