"""One icon per kind of action, the same in every window (plans/interface.md "Icons", UI-2): Lucide SVGs (ISC
licence, resources/icons/lucide/) and our own astronomy drawings on the same 24 × 24 grid (resources/icons/own/),
tinted with the theme's text colour (faint when disabled, accent when checked) and drawn at the screen's pixel ratio.
No file serves two kinds (a test checks it).
"""

from functools import cache
from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap

ROOT = Path(__file__).resolve().parents[2] / "resources" / "icons"
SIZE = 20

ICONS = {
    # areas (the start window's blocks, the Window menu)
    "area_plan": "own/area_plan",
    "area_observe": "own/area_observe",
    "area_calibrate": "own/area_calibrate",
    "area_image": "own/area_image",
    "area_astrometry": "own/area_astrometry",
    "area_photometry": "own/area_photometry",
    "area_timeseries": "own/area_timeseries",
    "area_oc": "own/area_oc",
    "area_exoplanets": "own/area_exoplanets",
    "area_spectroscopy": "own/area_spectroscopy",
    "area_orbits": "own/area_orbits",
    "area_remotesensing": "own/area_remotesensing",
    "area_automation": "own/area_automation",
    # files
    "open": "lucide/folder-open",
    "open_folder": "lucide/folder-plus",
    "save": "lucide/save",
    "export": "lucide/share",
    "publication": "lucide/file-chart-line",
    "new_window": "lucide/picture-in-picture-2",
    # frames and the image
    "previous": "lucide/chevron-left",
    "next": "lucide/chevron-right",
    "blink": "own/blink",
    "fit": "lucide/maximize",
    "zoom_in": "lucide/zoom-in",
    "zoom_out": "lucide/zoom-out",
    "levels": "lucide/contrast",
    "overlays": "lucide/layers",
    "process": "lucide/wand-sparkles",
    "solve": "own/solve",
    # photometry
    "bad_frames": "lucide/image-off",
    "comparisons": "own/comparisons",
    "radii": "own/radii",
    "measure": "own/measure",
    "minimum": "own/minimum",
    "leave_out": "lucide/eraser",
    # calibration
    "scan": "lucide/scan-search",
    "calibrate": "own/calibrate",
    "stack": "lucide/layers-2",
    "send": "lucide/arrow-right-from-line",
    # planning and observing
    "add_target": "own/add_target",
    "ephemeris": "lucide/calendar-clock",
    "plan_night": "lucide/moon-star",
    "exposure": "lucide/timer",
    "schedule": "lucide/list-ordered",
    "connect": "lucide/plug",
    "slew": "own/slew",
    "centre": "lucide/locate-fixed",
    "park": "lucide/house",
    "preview": "lucide/camera",
    "autofocus": "lucide/focus",
    "start": "lucide/play",
    "abort": "lucide/square",
    # automation and remote sensing
    "new": "lucide/file-plus",
    "add_step": "lucide/list-plus",
    "compute": "lucide/calculator",
    "classify": "lucide/grid-3x3",
    "pca": "lucide/axis-3d",
    # light curves and O−C
    "download": "lucide/download",
    "period_search": "own/period_search",
    "frequency": "lucide/audio-waveform",
    "variable_search": "own/variable_search",
    "lookup": "lucide/search",
    "fit_model": "lucide/chart-spline",
    # models
    "posterior": "own/posterior",
    "visual_orbit": "lucide/orbit",
    # spectroscopy jobs
    "long_slit": "own/long_slit",
    "echelle": "own/echelle",
    "telluric": "own/telluric",
    "velocity": "own/velocity",
    "cube": "lucide/box",
    "spectrum_tools": "lucide/chart-line",
    # images: Process and Overlays (the Images window), View → Orientation
    "flip_lr": "lucide/flip-horizontal-2",
    "flip_tb": "lucide/flip-vertical-2",
    "rotate_90": "lucide/rotate-cw",
    "rotate_any": "lucide/rotate-cw-square",
    "original_orientation": "lucide/rotate-ccw",
    "north_up": "lucide/compass",
    "resample": "lucide/scaling",
    "bin": "lucide/shrink",
    "crop": "lucide/crop",
    "gaussian": "lucide/droplets",
    "median": "lucide/filter",
    "unsharp": "lucide/sparkle",
    "background": "lucide/sun-dim",
    "kernel": "lucide/square-function",
    "deconvolve": "lucide/circle-dot",
    "ddp": "lucide/sun-medium",
    "histogram_match": "lucide/chart-column",
    "contours": "lucide/waves",
    "coordinate_grid": "lucide/grid-2x2",
    "catalogue_stars": "lucide/sparkles",
    "minor_planets": "lucide/circle-dot-dashed",
    "finder_chart": "lucide/map",
    "clear": "lucide/trash-2",
    # every window's View, Edit, Tools and Help menus
    "larger_text": "lucide/a-arrow-up",
    "smaller_text": "lucide/a-arrow-down",
    "normal_text": "lucide/a-large-small",
    "reset_layout": "lucide/layout-dashboard",
    "copy": "lucide/copy",
    "earth_tables": "lucide/earth",
    "clear_cache": "lucide/database-zap",
    "converter": "lucide/arrow-left-right",
    "camera_measure": "lucide/aperture",
    "edit_headers": "lucide/file-pen-line",
    "whats_this": "lucide/message-circle-question",
    "shortcuts": "lucide/keyboard",
    "report": "lucide/bug",
    "tour": "lucide/signpost",
    "full_tour": "lucide/route",
    "area_tour": "lucide/map-pin",
    "updates": "lucide/refresh-cw",
    "about": "lucide/badge-info",
    # general
    "undo": "lucide/undo-2",
    "redo": "lucide/redo-2",
    "settings": "lucide/settings",
    "help": "lucide/circle-help",
    "tasks": "lucide/list-checks",
    "info": "lucide/info",
    "warning": "lucide/triangle-alert",
    "error": "lucide/circle-x",
    "close": "lucide/x",
    "more": "lucide/ellipsis",
}


@cache
def _svg(kind):
    text = (ROOT / f"{ICONS[kind]}.svg").read_text(encoding="utf-8")
    return text.replace('stroke-width="2"', 'stroke-width="1.75"')  # Lucide's 2 px to the design system's 1.75


def _pixmap(kind, colour, size, ratio):
    from PySide6.QtSvg import QSvgRenderer

    data = QByteArray(_svg(kind).replace("currentColor", colour).encode("utf-8"))
    side = round(size * ratio)
    pixmap = QPixmap(side, side)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    QSvgRenderer(data).render(painter, QRectF(0, 0, side, side))
    painter.end()
    pixmap.setDevicePixelRatio(ratio)
    return pixmap


def icon(kind, widget, size=SIZE):
    """The icon of a kind of action for a widget: the theme's text colour, faint when disabled, accent when checked."""
    pal = widget.palette()
    ratio = max(1.0, widget.devicePixelRatioF())
    out = QIcon()
    for mode, state, role in (
        (QIcon.Normal, QIcon.Off, pal.ColorRole.WindowText),
        (QIcon.Disabled, QIcon.Off, pal.ColorRole.PlaceholderText),
        (QIcon.Normal, QIcon.On, pal.ColorRole.Highlight),
    ):
        out.addPixmap(_pixmap(kind, pal.color(role).name(), size, ratio), mode, state)
    return out
