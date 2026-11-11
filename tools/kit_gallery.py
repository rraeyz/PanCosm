"""Every component of the kit in its states, for looking at (plans/interface.md UI-3 item 4).

python tools/kit_gallery.py                       # a window
python tools/kit_gallery.py --shot out.png [--light]   # a picture, for review and the UI-1 screenshots
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def gallery(light=False):
    from PySide6.QtWidgets import QApplication, QGridLayout, QLabel, QVBoxLayout, QWidget

    from astrowb.ui import theme
    from astrowb.ui.kit.banners import Badge, InfoBanner
    from astrowb.ui.kit.buttons import KINDS, Button
    from astrowb.ui.kit.empty import EmptyState
    from astrowb.ui.kit.fields import NumberField, PathField, Segmented
    from astrowb.ui.kit.forms import FormRow
    from astrowb.ui.kit.inspector import Inspector
    from astrowb.ui.kit.sections import Section

    app = QApplication.instance() or QApplication([])
    theme.apply(app, "light" if light else "dark")
    page = QWidget()
    page.setWindowTitle("Kit gallery")
    grid = QGridLayout(page)
    left, right = QVBoxLayout(), QVBoxLayout()
    grid.addLayout(left, 0, 0)
    grid.addLayout(right, 0, 1)

    buttons = QWidget()
    row = QGridLayout(buttons)
    for i, kind in enumerate(KINDS):
        row.addWidget(Button(kind.title(), kind, icon="measure" if kind == "primary" else None), 0, i)
        off = Button(kind.title(), kind)
        off.setEnabled(False)
        row.addWidget(off, 1, i)
    busy = Button("Measuring", "primary")
    busy.set_busy(True)
    row.addWidget(busy, 2, 0)
    left.addWidget(buttons)

    section = Section("Apertures", help="photometry-apertures")
    section.body.addWidget(FormRow("Aperture radius", NumberField(5, 1, 50, 0.5, 1), unit="px"))
    changed = NumberField(8, 1, 50, 0.5, 1)
    form = FormRow("Inner sky radius", changed, unit="px")
    changed.setValue(12)
    section.body.addWidget(form)
    auto = NumberField(3, 0, 10, allow_auto=True)
    auto.set_auto(True, shown=4.2)
    section.body.addWidget(FormRow("Outer sky radius", auto, unit="px"))
    section.body.addWidget(FormRow("Time axis", Segmented([("bjd", "BJD"), ("phase", "Phase"), ("ut", "UT")])))
    missing = PathField("files")
    missing.set_paths(["/no/such/light_V_000.fits", "/no/such/light_V_001.fits"])
    section.body.addWidget(FormRow("Frames", missing, reset=False))
    left.addWidget(section)
    folded = Section("Advanced", folded=True, advanced=True)
    left.addWidget(folded)
    for kind in ("info", "ok", "attention", "error"):
        left.addWidget(InfoBanner(kind, f"An {kind} banner with a sentence long enough to show how it wraps.",
                                  [("Act", lambda: None)] if kind == "attention" else ()))  # fmt: skip
    badges = QWidget()
    brow = QGridLayout(badges)
    for i, (text, kind) in enumerate((("calibrated", "ok"), ("from cache", "info"), ("simulated", "attention"))):
        brow.addWidget(Badge(text, kind), 0, i)
    left.addWidget(badges)
    left.addStretch(1)

    panel = Inspector("Star")
    panel.set_rows([("Flux", 12345.6, "ADU"), ("FWHM", 3.2, "px"), ("BJD", 2460512.345678, ""), ("Name", "V1234 Cyg")])
    right.addWidget(panel)
    right.addWidget(EmptyState("open", "No images yet", "Open FITS files to look at them.",
                               ("Open images…", lambda: None), sample=lambda: None))  # fmt: skip
    right.addWidget(QLabel(""))
    page.resize(1100, 760)
    return app, page


if __name__ == "__main__":
    shot = sys.argv[sys.argv.index("--shot") + 1] if "--shot" in sys.argv else None
    if shot:
        import os

        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app, page = gallery(light="--light" in sys.argv)
    page.show()
    if shot:
        app.processEvents()
        page.grab().save(shot)
        print(shot)
    else:
        app.exec()
