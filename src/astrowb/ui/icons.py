"""One icon per kind of action, the same in every window (plans/interface.md I6c.1): Qt's standard icons where they
fit, otherwise a symbol of the interface font drawn in the theme's text colour (as AstroImageJ's small toolbar
icons). No symbol serves two kinds (a test checks it)."""

from PySide6.QtWidgets import QStyle

from .widgets import glyph

ICONS = {
    # files
    "open": QStyle.SP_DialogOpenButton,
    "open_folder": QStyle.SP_DirOpenIcon,
    "save": QStyle.SP_DialogSaveButton,
    "export": "⇪",
    # frames and the image
    "previous": "◀",
    "next": "▶",
    "blink": "⇆",
    "fit": "⤢",
    "zoom_in": "+",
    "zoom_out": "−",
    "levels": "◐",
    "overlays": "▦",
    "process": "ƒ",
    "solve": "⊕",
    # photometry
    "bad_frames": "⚑",
    "comparisons": "✶",
    "radii": "◎",
    "measure": "✦",
    "minimum": "⋎",
    # calibration
    "scan": "⌕",
    "calibrate": "◑",
    "stack": "⧈",
    "send": "➜",
    # light curves and O−C
    "download": "⇓",
    "period_search": "⟲",
    "frequency": "ν",
    "variable_search": "✧",
    "lookup": "ℹ",
    "fit_model": "⟋",
    # spectroscopy jobs
    "long_slit": "▭",
    "echelle": "≣",
    "telluric": "≈",
    "velocity": "⇋",
    "cube": "⧉",
    "spectrum_tools": "✎",
}


def icon(kind, widget):
    """The icon of a kind of action for a widget (its style and text colour)."""
    spec = ICONS[kind]
    if isinstance(spec, str):
        return glyph(spec, widget.palette().windowText().color())
    return widget.style().standardIcon(spec)
