"""Stars picked by hand on one frame (stacking's "on stars I pick" alignment, the owner's 2026-11-13 request): the
frame in a viewer, each click snaps onto the nearest star and is marked, a click on a marked star takes it off."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QLabel

from .kit.dialogs import Dialog
from .viewer import ImageViewer

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("StarPicker", "…") calls


class StarPicker(Dialog):
    def __init__(self, path, stars=(), parent=None):
        from ..calibration.masters import load

        super().__init__(translate("StarPicker", "Stars to align on"), parent, None, "star_picker")
        self.stars = [tuple(map(float, s)) for s in stars]
        self.body.addWidget(
            QLabel(
                translate("StarPicker", "Click one or more stars that every frame shows; click again to take one off.")
            )
        )
        self.viewer = ImageViewer(self)
        self.viewer.set_image(load(path)[0])
        self.viewer.clicked.connect(self.click)
        self.body.addWidget(self.viewer, 1)
        self.add_buttons(translate("StarPicker", "Use these stars"), translate("StarPicker", "Cancel"))
        self.resize(820, 680)
        self._draw()

    def click(self, x, y):
        from ..photometry.aperture import snap_to_star

        near = [s for s in self.stars if (s[0] - x) ** 2 + (s[1] - y) ** 2 <= 36]
        if near:
            self.stars.remove(near[0])
        else:
            scale = abs(self.viewer.transform().m11()) or 1.0
            sx, sy = snap_to_star(self.viewer.data, [(x, y)], radius=max(4.0, 3.0 / scale))[0]
            self.stars.append((round(float(sx), 2), round(float(sy), 2)))
        self._draw()

    def _draw(self):
        self.viewer.set_markers([(x, y, 8, "lime", str(k + 1)) for k, (x, y) in enumerate(self.stars)])


def as_text(stars):
    return "; ".join(f"{x:.1f} {y:.1f}" for x, y in stars)


def parse(text):
    """'x y; x y' -> [(x, y)]; ValueError on anything else."""
    out = []
    for part in text.replace(",", " ").split(";"):
        if part.strip():
            nums = [float(v) for v in part.split()]
            if len(nums) != 2:
                raise ValueError(part)
            out.append(tuple(nums))
    return out


def add_align_row(page, layout, grid):
    """Stacking options: alignment off, or on stars picked on the first frame (with the field to type them in and the
    button that opens the picker)."""
    from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton

    layout.addLayout(grid)
    box = page.stack_opts["align"]
    box.addItem(translate("StarPicker", "none (the frames are aligned already)"), "none")
    box.addItem(translate("StarPicker", "on stars I pick"), "picked")
    row = QHBoxLayout()
    page.align_stars = QLineEdit(page)
    page.align_stars.setPlaceholderText(translate("StarPicker", "x y; x y … on the first frame"))
    page.align_stars.setToolTip(
        translate("StarPicker", "The stars every frame is aligned on, followed from frame to frame (shift only)")
    )
    pick = page.pick_align_stars = QPushButton(translate("StarPicker", "Pick on the first frame…"), page)

    def open_picker():
        from ..timing import chronological

        frames = chronological(getattr(page, "calibrated", None) or [])  # the first in time: where stacking starts
        if not frames:
            page.result.setText(translate("StarPicker", "Calibrate the lights first: the stars are picked on them."))
            return
        try:
            stars = parse(page.align_stars.text())
        except ValueError:
            stars = []
        dlg = StarPicker(frames[0], stars, page)
        if dlg.exec():
            page.align_stars.setText(as_text(dlg.stars))
            box.setCurrentIndex(box.findData("picked"))

    pick.clicked.connect(open_picker)
    row.addWidget(page.align_stars, 1)
    row.addWidget(pick)
    layout.addLayout(row)


def choose_alignment(parent, first_image):
    """Asked before the Images window stacks: how the frames are aligned. Returns stacking parameters ({"align",
    "align_stars"}) or None when cancelled."""
    from PySide6.QtWidgets import QInputDialog

    choices = [("translation", translate("StarPicker", "shift only (automatic)")),
               ("stars", translate("StarPicker", "star patterns: rotation and scale too (automatic)")),
               ("none", translate("StarPicker", "none (the frames are aligned already)")),
               ("picked", translate("StarPicker", "on stars I pick"))]  # fmt: skip
    text, ok = QInputDialog.getItem(parent, translate("StarPicker", "Align the images"),
                                    translate("StarPicker", "How are the images aligned before stacking?"),
                                    [t for _, t in choices], 0, False)  # fmt: skip
    if not ok:
        return None
    align = next(k for k, t in choices if t == text)
    if align != "picked":
        return {"align": align}
    dlg = StarPicker(first_image, (), parent)
    if not dlg.exec() or not dlg.stars:
        return None
    return {"align": "picked", "align_stars": [list(s) for s in dlg.stars]}
