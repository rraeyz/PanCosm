"""The Images window's Overlays menu: contours, coordinate grid, catalogue stars and DS9 regions on the image."""

from pathlib import Path

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QFileDialog, QInputDialog

from .. import overlays


def add_menu(win, menu):
    sub = menu.addMenu(QCoreApplication.translate("Overlays", "&Overlays"))
    win._action(sub, QCoreApplication.translate("Overlays", "Contours…"), lambda: contours(win))
    win._action(sub, QCoreApplication.translate("Overlays", "Coordinate grid"), lambda: grid(win))
    win._action(
        sub, QCoreApplication.translate("Overlays", "Catalogue stars (Gaia DR3)…"), lambda: catalogue(win, "gaia")
    )
    win._action(
        sub, QCoreApplication.translate("Overlays", "Variable stars (VSX)"), lambda: catalogue(win, "vsx", 30.0)
    )
    win._action(
        sub, QCoreApplication.translate("Overlays", "Asteroids and comets (SkyBoT)"), lambda: minor_planets(win)
    )
    win._action(sub, QCoreApplication.translate("Overlays", "Finder chart…"), lambda: finder_chart(win))
    sub.addSeparator()
    win._action(sub, QCoreApplication.translate("Overlays", "Load DS9 regions…"), lambda: load_regions(win))
    win._action(sub, QCoreApplication.translate("Overlays", "Save markers as DS9 regions…"), lambda: save_regions(win))
    win._action(
        sub,
        QCoreApplication.translate("Overlays", "Clear overlays"),
        lambda: [win.viewer.set_overlay(n) for n in win.viewer.overlay_names()],
    )
    return sub


def _status(win, text):
    win.statusBar().showMessage(text, 8000)


def contours(win, n=None):
    if win.viewer.data is None:
        return None
    if n is None:
        n, ok = QInputDialog.getInt(
            win,
            QCoreApplication.translate("Overlays", "Contours"),
            QCoreApplication.translate("Overlays", "Number of levels:"),
            6,
            1,
            30,
        )
        if not ok:
            return None
    levels = overlays.contour_levels(win.viewer.data, n)
    lines = [line for ls in overlays.contours(win.viewer.data, levels).values() for line in ls]
    win.viewer.set_overlay("contours", "#7CFC00", lines=lines)
    return len(lines)


def grid(win):
    if win.viewer.data is None:
        return None
    if win.wcs is None:
        _status(
            win,
            QCoreApplication.translate(
                "Overlays", "The image has no sky coordinates: plate-solve it first (Image menu)."
            ),
        )
        return None
    g = overlays.wcs_grid(win.wcs, win.viewer.data.shape)
    texts = [(*line[len(line) // 2], label) for _, _, line, label in g]
    win.viewer.set_overlay("grid", "#ffd60a", lines=[line for _, _, line, _ in g], texts=texts)
    return len(g)


def catalogue(win, which, mag_limit=None):
    if getattr(win, "current_path", None) is None:
        return None
    if win.wcs is None:
        _status(
            win,
            QCoreApplication.translate(
                "Overlays", "The image has no sky coordinates: plate-solve it first (Image menu)."
            ),
        )
        return None
    if mag_limit is None:
        mag_limit, ok = QInputDialog.getDouble(
            win,
            QCoreApplication.translate("Overlays", "Catalogue stars"),
            QCoreApplication.translate("Overlays", "Faintest magnitude:"),
            16,
            5,
            21,
            1,
        )
        if not ok:
            return None
    _status(win, QCoreApplication.translate("Overlays", "Querying the catalogue…"))
    return win.run_step(
        "image.catalogue",
        {"image": str(win.current_path)},
        {"catalogue": which, "mag_limit": mag_limit},
        on_done=lambda out: show_catalogue(win, which, out["stars"]),
    )


def finder_chart(win, target=None, output=None, use_dss=None):
    """A finder chart of the current plate-solved image, or a DSS chart around a typed target (no image needed)."""
    from ..planning.targets import parse_coordinates

    image = str(win.current_path) if getattr(win, "current_path", None) is not None and win.wcs is not None else None
    inputs = {}
    if use_dss is None:
        use_dss = image is None
    if use_dss:
        if target is None:
            text, ok = QInputDialog.getText(
                win,
                QCoreApplication.translate("Overlays", "Finder chart"),
                QCoreApplication.translate("Overlays", "Target coordinates (RA Dec), e.g. 02:04:10 +46:41:16:"),
            )
            if not ok:
                return None
            target = parse_coordinates(text)
            if target is None:
                _status(win, QCoreApplication.translate("Overlays", "Coordinates not understood."))
                return None
        inputs |= {"ra": float(target.ra.deg), "dec": float(target.dec.deg)}
    else:
        inputs["image"] = image
    if output is None:
        output = QFileDialog.getSaveFileName(
            win, QCoreApplication.translate("Overlays", "Finder chart"), "chart.png", "PNG (*.png);;PDF (*.pdf)"
        )[0]
        if not output:
            return None
    inputs["output"] = output
    _status(win, QCoreApplication.translate("Overlays", "Making the finder chart…"))
    return win.run_step("image.finder_chart", inputs, {}, on_done=lambda out: win.show_picture(out["chart"]))


def minor_planets(win):
    """Known asteroids and comets in the field at the image's time (the image must be plate-solved)."""
    if getattr(win, "current_path", None) is None:
        return None
    if win.wcs is None:
        _status(
            win,
            QCoreApplication.translate(
                "Overlays", "The image has no sky coordinates: plate-solve it first (Image menu)."
            ),
        )
        return None
    _status(win, QCoreApplication.translate("Overlays", "Querying the catalogue…"))
    return win.run_step(
        "image.minor_planets",
        {"image": str(win.current_path)},
        {},
        on_done=lambda out: show_catalogue(win, "minor", out["objects"]),
    )


def show_catalogue(win, which, stars):
    colour = {"vsx": "#ff4fd8", "minor": "#ffb000"}.get(which, "#4fc3ff")
    if which in ("vsx", "minor"):
        label = lambda s: s["name"]  # noqa: E731
    else:
        label = lambda s: f"{s['mag']:.1f}" if s["mag"] is not None else ""  # noqa: E731
    win.viewer.set_overlay(which, colour, circles=[(s["x"], s["y"], 6, label(s)) for s in stars])
    if len(stars) > win.viewer.MAX_LABELS:
        _status(
            win,
            QCoreApplication.translate("Overlays", "{n} catalogue stars shown: point at a ring for its label.").format(
                n=len(stars)
            ),
        )
    else:
        _status(win, QCoreApplication.translate("Overlays", "{n} catalogue stars shown.").format(n=len(stars)))


def load_regions(win, path=None):
    if win.viewer.data is None:
        return None
    path = (
        path
        or QFileDialog.getOpenFileName(
            win, QCoreApplication.translate("Overlays", "DS9 regions"), "", "DS9 (*.reg);;*"
        )[0]
    )
    if not path:
        return None
    regs = overlays.read_regions(Path(path).read_text(encoding="utf-8", errors="replace"), win.wcs)
    circles = [(r["x"], r["y"], r["r"], r["text"]) for r in regs if r["shape"] == "circle"]
    lines = [[(r["x"], r["y"]), (r["x2"], r["y2"])] for r in regs if r["shape"] == "line"]
    for r in regs:
        if r["shape"] in ("box", "ellipse"):
            import numpy as np

            hw, hh, a = r["w"] / 2, r["h"] / 2, np.radians(r["angle"])
            corners = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh), (-hw, -hh)]
            c, s = np.cos(a), np.sin(a)
            lines.append([(r["x"] + c * u - s * v, r["y"] + s * u + c * v) for u, v in corners])
    texts = [(r["x"], r["y"], r["text"] or "+") for r in regs if r["shape"] in ("point", "text")]
    win.viewer.set_overlay("regions", "#00ff7f", lines=lines, circles=circles, texts=texts)
    return regs


def save_regions(win, path=None):
    markers = getattr(win.viewer, "marker_list", [])
    if not markers:
        _status(
            win,
            QCoreApplication.translate(
                "Overlays", "No markers on the image (stars picked in the Photometry window are markers)."
            ),
        )
        return None
    path = (
        path
        or QFileDialog.getSaveFileName(
            win, QCoreApplication.translate("Overlays", "DS9 regions"), "markers.reg", "DS9 (*.reg)"
        )[0]
    )
    if not path:
        return None
    regs = [{"shape": "circle", "x": m[0], "y": m[1], "r": m[2], "text": m[4]} for m in markers]
    Path(path).write_text(overlays.write_regions(regs, win.wcs), encoding="utf-8")
    return path
