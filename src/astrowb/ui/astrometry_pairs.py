"""PHO-24 in the Astrometry window: a line drawn between two stars on the shown frame measures the pair (the Images
window's `pair_of`) and offers it to the same Pairs table. Clicks pick the moving object, so the line is a mode."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QPushButton

from .image_pair import pair_of
from .image_pair_table import PairTable

translate = QCoreApplication.translate


def pair_widgets(page):
    """The Find stage's toggle and the Pairs table (hidden until a pair is measured)."""
    b = QPushButton(translate("MovingObjectPage", "Measure a pair of stars"), page)
    b.setCheckable(True)
    b.setEnabled(False)
    b.setToolTip(
        translate(
            "MovingObjectPage",
            "While on, drag a line from one star to another: separation, position angle, flux ratio and Δmag",
        )
    )
    b.toggled.connect(lambda on: line_mode(page, on))
    page.pair_table = PairTable(page)
    page.pair_table.hide()
    return b, page.pair_table


def connect(page):
    """Once the page's viewer exists: its lines measure pairs."""
    page.viewer.line_selected.connect(lambda *ends: measure_pair(page, *ends))


def line_mode(page, on):
    page.viewer.set_pick(not on)  # off: clicks pick the object again
    page.viewer.set_tool("line" if on else "pan")
    if not on:
        page.viewer.set_pick(True)  # the pick cross back over set_tool's hand
    page.viewer.show_selection(None, 0, 0, 0, 0)


def _shown_frame(page):
    # the first frame until the object is clicked there, then the last (as MovingObjectPage._clicked shows them)
    return page.images[-1] if page.first is not None else page.images[0]


def measure_pair(page, x0, y0, x1, y1):
    from astropy.wcs import WCS

    from ..io.fits import read_image

    if page.viewer.data is None or not page.images:
        return None
    try:
        wcs = WCS(read_image(_shown_frame(page))[1])
    except (OSError, ValueError):
        wcs = None  # no readable solution: the pair in pixels only
    p = pair_of(page.viewer.data, x0, y0, x1, y1, wcs if wcs is not None and wcs.has_celestial else None)
    page.pair_table.set_last(p)
    if p is None:
        page.hint.setText(translate("MovingObjectPage", "Both ends of the line must sit on stars."))
        return None
    page.pair_table.show()
    text = translate("MovingObjectPage", "Pair: separation {s:.2f} px, Δmag {d:.3f} ± {e:.3f}. Add it to the table.")
    page.hint.setText(text.format(s=p["separation_px"], d=p["dmag"], e=p["dmag_err"]))
    return p
