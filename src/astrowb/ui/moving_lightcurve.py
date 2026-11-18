"""The Astrometry window's "Light curve" stage (plans/photometry.md PHO-21): brightness of the moving object on every
frame (photometry/moving_lc.py), the curve and the frame list, and the ALCDEF file.

The comparison stars are the stars found on the first frame (photometry.fieldstars.detect_stars), followed to every
frame through its plate solution. No catalogue magnitudes are looked up here: each star's magnitude is its
instrumental one on the first frame (zero point 25), so the curve is on an internal system (ALCDEF STANDARD=INTERNAL).
"""

import threading

import numpy as np
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..core import profiles
from .kit.table_view import DataTable
from .plot.toolbar import plot_box

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("MovingLC", "…") calls
RADII = (4.0, 10.0, 16.0)  # the Photometry window's default aperture, sky ring inner and outer radii (px)
MARGIN = 2  # px beyond r_out a comparison star must lie inside the frame


def track_of(paths, rows, first, last):
    """(frames [(data, header)], JD, positions) in time order: the measured positions when there are any, else the
    straight track between the two marks (on the first and the last frame)."""
    from .. import timing
    from ..calibration.masters import load

    if rows:
        paths = [r["file"] for r in rows]
    elif first is None or last is None:
        raise ValueError("no object positions: mark the object on the first and the last frame")
    frames = [load(p) for p in paths]
    jd = np.array([timing.mid_time(h).utc.jd for _, h in frames])
    if rows:
        return frames, jd, np.array([(r["x"], r["y"]) for r in rows], float)
    from ..photometry.moving_lc import linear_track

    return frames, jd, linear_track(jd, (jd[0], *first), (jd[-1], *last))


def field_stars(frames, xy0, radii, gain):
    """Per frame [(x, y, mag)] of the first frame's stars (the object left out) at their places on that frame."""
    from astropy.wcs import WCS

    from ..photometry.aperture import measure as aperture_measure
    from ..photometry.fieldstars import detect_stars

    r_ap, r_in, r_out = radii
    data0 = frames[0][0]
    xy = detect_stars(data0)
    flux = aperture_measure(data0, xy, r_ap, r_in, r_out, gain)[0] if len(xy) else np.empty(0)
    keep = (flux > 0) & (np.hypot(*(xy - xy0).T) > r_out) if len(xy) else np.zeros(0, bool)
    if not keep.any():
        raise ValueError("no comparison stars found on the first frame")
    mag = 25 - 2.5 * np.log10(flux[keep])
    wcs0 = WCS(frames[0][1])
    if not wcs0.has_celestial:
        raise ValueError("the image has no sky coordinates: plate-solve it first (Image menu)")
    sky = wcs0.pixel_to_world_values(*xy[keep].T)
    out = []
    for data, header in frames:
        x, y = WCS(header).world_to_pixel_values(*sky)
        ny, nx = data.shape
        lo = r_out + MARGIN
        ok = (x > lo) & (x < nx - lo) & (y > lo) & (y < ny - lo)
        if ok.sum() < 3:
            raise ValueError("fewer than 3 comparison stars lie on a frame: the frames do not overlap enough")
        out.append(list(zip(x[ok], y[ok], mag[ok], strict=True)))
    return out


def compute(paths, rows, first, last, radii, gain=1.0):
    """The Measure stage's rows (else the two marks) → [{jd, x, y, mag, err, zp, n_stars, blended, file}] per frame."""
    from ..photometry import moving_lc

    frames, jd, track = track_of(paths, rows, first, last)
    stars = field_stars(frames, track[0], radii, gain)
    out = moving_lc.measure([d for d, _ in frames], track, stars, *radii, gain)
    names = [r["file"] for r in rows] if rows else list(paths)
    return [{"jd": float(t), "file": n, **r} for t, n, r in zip(jd, names, out, strict=True)]


def curve_figure(rows):
    """Magnitude (brighter up) against time with errors, the blended frames left out."""
    from .plot.spec import AxisSpec, FigureSpec, PanelSpec, SeriesSpec

    use = [r for r in rows if not r["blended"] and np.isfinite(r["mag"])]
    t0 = rows[0]["jd"]
    x = np.array([r["jd"] - t0 for r in use])
    ax = AxisSpec(translate("MovingLC", "Days since JD {t0:.5f}").format(t0=t0))
    return FigureSpec(
        [
            PanelSpec(
                ax,
                AxisSpec(translate("MovingLC", "Magnitude"), invert=True),
                [
                    SeriesSpec(
                        translate("MovingLC", "object"),
                        x,
                        [r["mag"] for r in use],
                        yerr=[r["err"] for r in use],
                    )
                ],
            )
        ]
    )


def stage_box(page):
    """The stage's widgets, kept on the page (lc_*); the plot and the list sit in the box under the button."""
    box = QWidget(page)
    lay = QVBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    form = QFormLayout()
    page.lc_radii = []
    for text, value in zip(
        (
            translate("MovingLC", "Aperture (px)"),
            translate("MovingLC", "Sky ring inner (px)"),
            translate("MovingLC", "Sky ring outer (px)"),
        ),
        RADII,
        strict=True,
    ):
        spin = QDoubleSpinBox(box)
        spin.setRange(0.5, 200)
        spin.setSingleStep(0.5)
        spin.setValue(value)
        form.addRow(text, spin)
        page.lc_radii.append(spin)
    lay.addLayout(form)
    page.lc_button = QPushButton(translate("MovingLC", "Measure brightness"), box)
    page.lc_button.setToolTip(
        translate(
            "MovingLC",
            "Measures the object on every frame against the stars of the field (magnitudes on an internal "
            "system, not a catalogue) and draws the light curve; frames where it passes a bright star are listed "
            "but left out of the curve and the file",
        )
    )
    page.lc_button.clicked.connect(lambda: start(page))
    page.lc_save = QPushButton(translate("MovingLC", "Save as ALCDEF…"), box)
    page.lc_save.setEnabled(False)
    page.lc_save.setToolTip(
        translate(
            "MovingLC",
            "Writes the curve as an ALCDEF file (standard 2.3.0) for the asteroid light-curve database",
        )
    )
    page.lc_save.clicked.connect(lambda: export(page))
    for w in (page.lc_button, page.lc_save):
        lay.addWidget(w)
    page.lc_rows = []
    return box


def show_widgets(page):
    """The plot and the list, shown in the page's right column under the frame."""
    plot_widget, page.lc_plot = plot_box(page)
    page.lc_table = DataTable(page)
    plot_widget.hide()
    page.lc_table.hide()
    return plot_widget, page.lc_table


def start(page):
    """Measure in a worker thread; the answer comes back to the window's thread. Every failure is said in the hint."""
    from .kit.handoff import to_main

    paths, rows = list(page.images), list(page.positions)
    first = page.first and tuple(page.first)
    last = page.last and tuple(page.last)
    radii = tuple(s.value() for s in page.lc_radii)
    if not paths and not rows:
        page.hint.setText(translate("MovingLC", "Choose the frames first."))
        return
    page.lc_button.setEnabled(False)
    deliver = to_main(page, lambda out, err: done(page, out, err))

    def work():
        from .messages import translate as message

        try:
            deliver(compute(paths, rows, first, last, radii), "")
        except (ValueError, OSError) as e:
            deliver([], message(str(e)))

    threading.Thread(target=work, daemon=True).start()


def done(page, rows, error):
    page.lc_button.setEnabled(True)
    page.lc_rows = rows
    page.lc_save.setEnabled(bool(rows))
    if error:
        page.hint.setText(error)
        return
    page.lc_plot.set_figure(curve_figure(rows))
    head = [
        translate("MovingLC", "UTC time (JD)"),
        translate("MovingLC", "Magnitude"),
        translate("MovingLC", "Error"),
        translate("MovingLC", "Stars"),
        translate("MovingLC", "Blended"),
    ]
    page.lc_table.set_data(
        head,
        [
            [
                round(r["jd"], 6),
                round(r["mag"], 3),
                round(r["err"], 3),
                r["n_stars"],
                translate("MovingLC", "yes") if r["blended"] else "",
            ]
            for r in rows
        ],
    )
    page.lc_plot.parentWidget().show()
    page.lc_table.show()
    left = sum(r["blended"] for r in rows)
    page.hint.setText(
        translate("MovingLC", "{n} frames measured, {k} blended with a star and left out of the curve.").format(
            n=len(rows), k=left
        )
    )


class AlcdefForm(QDialog):
    """The session keys the profile does not give; prefilled from the profile."""

    def __init__(self, fields, parent=None):
        from ..photometry.reports import alcdef

        super().__init__(parent)
        self.setWindowTitle(translate("MovingLC", "ALCDEF session"))
        form = QFormLayout(self)
        self.number = QSpinBox(self)
        self.number.setRange(0, 2**31 - 1)
        self.number.setToolTip(translate("MovingLC", "The minor planet's number; 0 when it has none"))
        self.name = QLineEdit(self)
        self.filter, self.band = QComboBox(self), QComboBox(self)
        self.filter.addItems(alcdef.FILTERS)
        self.band.addItems(alcdef.BANDS)
        self.contact, self.info, self.observers = QLineEdit(self), QLineEdit(self), QLineEdit(self)
        self.contact.setText(fields.get("contact_name", ""))
        self.observers.setText(fields.get("observers", ""))
        self.info.setPlaceholderText(translate("MovingLC", "an e-mail address"))
        self.band.setToolTip(translate("MovingLC", "The band the magnitudes are on"))
        for text, w in (
            (translate("MovingLC", "Object number"), self.number),
            (translate("MovingLC", "Object name"), self.name),
            (translate("MovingLC", "Filter"), self.filter),
            (translate("MovingLC", "Magnitude band"), self.band),
            (translate("MovingLC", "Contact name"), self.contact),
            (translate("MovingLC", "Contact info"), self.info),
            (translate("MovingLC", "Observers"), self.observers),
        ):
            form.addRow(text, w)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def values(self):
        return {
            "object_number": self.number.value(),
            "object_name": self.name.text().strip(),
            "filter": self.filter.currentText(),
            "magband": self.band.currentText(),
            "contact_name": self.contact.text().strip(),
            "contact_info": self.info.text().strip(),
            "observers": self.observers.text().strip(),
        }


def session(rows, keys, fields):
    """The ALCDEF session of the unblended frames: internal system, no light-time or distance reduction."""
    use = [r for r in rows if not r["blended"] and np.isfinite(r["mag"])]
    comment = translate(
        "MovingLC", "Magnitudes are instrumental magnitudes of the field stars on the first frame, not a catalogue"
    )
    return {
        "jd": [r["jd"] for r in use],
        "mag": [r["mag"] for r in use],
        "mag_err": [r["err"] for r in use],
        "differmags": False,
        "standard": "INTERNAL",
        "ltcapp": "NONE",
        "reducedmags": "NONE",
        "comments": [comment],
        **fields,
        **keys,
    }


def export(page, path=None, keys=None):
    """Write the file; the form asks for `keys` and a dialog for `path` unless given. A refusal is said, not raised."""
    from ..photometry.reports import alcdef
    from .messages import guarded
    from .messages import translate as message

    if not page.lc_rows:
        page.hint.setText(translate("MovingLC", "Measure the brightness first."))
        return None
    if keys is None:
        form = AlcdefForm(alcdef_fields(page), page)
        if not form.exec():
            return None
        keys = form.values()
    if path is None:
        path, _ = QFileDialog.getSaveFileName(
            page, translate("MovingLC", "ALCDEF file"), "alcdef.txt", "ALCDEF (*.txt)"
        )
    if not path:
        return None
    try:
        done_ = guarded(page, alcdef.write, path, session(page.lc_rows, keys, alcdef_fields(page)))
    except ValueError as e:
        page.hint.setText(message(str(e)))
        return None
    if done_ is not None:
        page.hint.setText(translate("MovingLC", "ALCDEF file written: {p}").format(p=path))
    return done_


def alcdef_fields(page):
    from ..photometry.reports import alcdef

    s = page.settings
    return alcdef.profile_fields({"observer": profiles.section(s, "observer"), "site": profiles.section(s, "site")})
