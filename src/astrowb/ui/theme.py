"""Application look: Fusion style with our own palette and style sheet, applied to every page, tab and
plot. Themes: dark (default, blue-black) and light. A saved theme that no longer exists falls back to dark.
The text size (points) is the user's (View → Larger / Smaller text), 10 pt by default.
"""

from pathlib import Path

from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette

from .kit import tokens

THEMES = tokens.THEMES
DEFAULT = tokens.DEFAULT
FONT_PT, FONT_MIN, FONT_MAX = 10.0, 7.0, 18.0


def colors(name):
    """The theme's tokens (kit/tokens.py) under the names the style sheet and older code use."""
    t = tokens.theme(name)
    return {
        "window": t["surface.0"], "panel": t["surface.1"], "raised": t["surface.2"], "hover": t["surface.3"],
        "text": t["text"], "muted": t["text.muted"], "faint": t["text.faint"], "accent": t["accent"],
        "accent_hover": t["accent.hover"], "accent_pressed": t["accent.pressed"], "accent_text": t["on.accent"],
        "border": t["border"], "border_strong": t["border.strong"], "ok": t["ok"], "attention": t["attention"],
        "error": t["error"], "image": t["image.background"],
    }  # fmt: skip


def style_sheet(c, font_pt=FONT_PT):
    big, small = f"{font_pt * 1.1:g}pt", f"{font_pt * 0.8:g}pt"
    return f"""
* {{ font-size: {font_pt:g}pt; }}
QWidget {{ color: {c["text"]}; }}
QMainWindow, QDialog {{ background: {c["window"]}; }}
QToolTip {{ background: {c["raised"]}; color: {c["text"]}; border: 1px solid {c["border"]}; padding: 4px; }}
QLabel[muted="true"] {{ color: {c["muted"]}; }}
QListWidget#sidebar {{
    background: {c["panel"]}; border: none; border-right: 1px solid {c["border"]};
    font-size: {big}; padding: 8px 6px; outline: 0;
}}
QListWidget#sidebar::item {{ padding: 6px 12px; margin: 1px 0; border-radius: 8px; }}
QListWidget#sidebar::item:hover {{ background: {c["raised"]}; }}
QListWidget#sidebar::item:selected {{ background: {c["accent"]}; color: {c["accent_text"]}; }}
QListWidget#sidebar::item:disabled {{
    background: transparent; color: {c["muted"]}; font-size: {small}; font-weight: bold; padding: 8px 12px 0px 12px;
}}
QPushButton {{
    background: {c["raised"]}; border: 1px solid {c["border"]}; border-radius: 7px;
    padding: 6px 14px; min-height: 18px;
}}
QPushButton:hover {{ background: {c["hover"]}; border-color: {c["border_strong"]}; }}
QPushButton:pressed, QPushButton:checked {{ background: {c["accent_pressed"]}; color: {c["accent_text"]}; }}
QPushButton:disabled {{ color: {c["faint"]}; border-color: {c["raised"]}; }}
QPushButton:focus, QToolButton:focus {{ border: 2px solid {c["accent"]}; }}
QPushButton:default, QPushButton[primary="true"] {{
    background: {c["accent"]}; color: {c["accent_text"]}; border: none;
}}
QPushButton:default:hover, QPushButton[primary="true"]:hover {{ background: {c["accent_hover"]}; }}
QPushButton[kind="quiet"] {{ background: transparent; border-color: transparent; }}
QPushButton[kind="quiet"]:hover {{ background: {c["hover"]}; }}
QPushButton[kind="danger"] {{ color: {c["error"]}; border-color: {c["error"]}; }}
QPushButton[kind="danger"]:disabled {{ color: {c["faint"]}; border-color: {c["raised"]}; }}
QPushButton[kind="quiet"]:disabled {{ color: {c["faint"]}; border-color: transparent; }}
QSpinBox, QDoubleSpinBox, QComboBox {{ min-height: 24px; }}  /* frames and arrows: Fusion + palette */
QLineEdit, QPlainTextEdit, QTextEdit, QTextBrowser {{
    background: {c["panel"]}; border: 1px solid {c["border"]}; border-radius: 6px; padding: 4px 6px;
    selection-background-color: {c["accent"]}; selection-color: {c["accent_text"]};
}}
QLineEdit:focus, QPlainTextEdit:focus {{
    border-color: {c["accent"]};
}}
QTabWidget::pane {{ border: 1px solid {c["border"]}; border-radius: 8px; top: -1px; background: {c["window"]}; }}
QTabBar {{ qproperty-drawBase: 0; }}
QTabBar::tab {{
    background: transparent; color: {c["muted"]}; padding: 8px 16px; margin-right: 2px;
    border-bottom: 2px solid transparent;
}}
QTabBar::tab:hover {{ color: {c["text"]}; }}
QTabBar::tab:selected {{ color: {c["text"]}; border-bottom: 2px solid {c["accent"]}; }}
QTableWidget, QTableView, QListWidget, QTreeWidget {{
    background: {c["panel"]}; alternate-background-color: {c["raised"]}; border: 1px solid {c["border"]};
    border-radius: 6px; gridline-color: {c["border"]};
    selection-background-color: {c["accent"]}; selection-color: {c["accent_text"]};
}}
QHeaderView::section {{
    background: {c["raised"]}; color: {c["muted"]}; border: none; border-bottom: 1px solid {c["border"]};
    border-right: 1px solid {c["border"]}; padding: 5px 8px;
}}
QMenuBar {{ background: {c["window"]}; }}
QMenuBar::item:selected, QMenu::item:selected {{ background: {c["accent"]}; color: {c["accent_text"]}; }}
QMenu {{ background: {c["panel"]}; border: 1px solid {c["border"]}; padding: 4px; }}
QMenu::item {{ padding: 5px 20px; border-radius: 5px; }}
QStatusBar {{ background: {c["panel"]}; color: {c["muted"]}; }}
QProgressBar {{ background: {c["panel"]}; border: 1px solid {c["border"]}; border-radius: 6px; text-align: center; }}
QProgressBar::chunk {{ background: {c["accent"]}; border-radius: 6px; }}
QSplitter::handle {{ background: {c["border"]}; }}
QSplitter::handle:horizontal {{ width: 1px; }}
QSplitter::handle:vertical {{ height: 1px; }}
QScrollBar:vertical {{ background: transparent; width: 10px; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; }}
QScrollBar::handle {{ background: {c["border"]}; border-radius: 5px; min-height: 24px; min-width: 24px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QCheckBox::indicator, QRadioButton::indicator {{ width: 15px; height: 15px; }}
QDockWidget::title {{ background: {c["panel"]}; padding: 5px; }}
QGraphicsView {{ background: {c["image"]}; border: none; }}
"""


FONTS = Path(__file__).resolve().parents[1] / "resources" / "fonts"  # Inter, JetBrains Mono (SIL OFL 1.1)
MONO = "JetBrains Mono"  # numbers in tables, read-outs, logs
_families = []


def load_fonts():
    """Register the bundled fonts once; returns the interface family ("" when they cannot be read)."""
    if not _families:
        for f in sorted(FONTS.glob("*.ttf")):
            i = QFontDatabase.addApplicationFont(str(f))
            _families.extend(QFontDatabase.applicationFontFamilies(i) if i >= 0 else [])
        _families.append("")  # tried: not again
    return next((f for f in _families if f.startswith("Inter")), "")  # "Inter Variable" from the variable file


def font_size(settings):
    """The user's text size in points, kept within the range the windows are tested at."""
    try:
        return min(FONT_MAX, max(FONT_MIN, float(settings.get("ui.font_pt", FONT_PT))))
    except (TypeError, ValueError):
        return FONT_PT


def apply(app, name=DEFAULT, font_pt=FONT_PT):
    """Apply a theme and text size to the whole application (widgets and matplotlib plots)."""
    import matplotlib as mpl

    c = colors(name)
    app.setStyle("Fusion")
    family = load_fonts()
    if family:
        font = QFont(family)
        font.setPointSizeF(font_pt)
        if hasattr(font, "setFeature"):  # Qt 6.7+: figures of one width, so columns of numbers line up
            font.setFeature(QFont.Tag("tnum"), 1)
        app.setFont(font)
    pal = QPalette()
    for role, key in (
        (QPalette.Window, "window"),
        (QPalette.Base, "panel"),
        (QPalette.AlternateBase, "raised"),
        (QPalette.Button, "raised"),
        (QPalette.Text, "text"),
        (QPalette.WindowText, "text"),
        (QPalette.ButtonText, "text"),
        (QPalette.ToolTipBase, "raised"),
        (QPalette.ToolTipText, "text"),
        (QPalette.PlaceholderText, "muted"),
        (QPalette.Highlight, "accent"),
        (QPalette.HighlightedText, "accent_text"),
        (QPalette.Link, "accent"),
    ):
        pal.setColor(role, QColor(c[key]))
    pal.setColor(QPalette.Disabled, QPalette.Text, QColor(c["faint"]))
    pal.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(c["faint"]))
    app.setPalette(pal)
    app.setStyleSheet(style_sheet(c, font_pt))
    cycle = [*tokens.SERIES, c["muted"]]  # the plot series palette of the design system
    mpl.rcParams.update(
        {
            "font.size": font_pt,
            "figure.facecolor": c["window"],
            "axes.facecolor": c["panel"],
            "savefig.facecolor": "auto",  # the toolbar's Save keeps what is on screen; print: "Publication figure…"
            "axes.edgecolor": c["border"],
            "axes.labelcolor": c["text"],
            "text.color": c["text"],
            "xtick.color": c["muted"],
            "ytick.color": c["muted"],
            "grid.color": c["border"],
            "legend.facecolor": c["raised"],
            "legend.edgecolor": c["border"],
            "axes.prop_cycle": mpl.cycler(color=cycle),
        }
    )
    return c


def change_font(app, settings, step):
    """step +1 / -1 one point larger / smaller, 0 back to the default; applied at once to every window."""
    size = FONT_PT if step == 0 else min(FONT_MAX, max(FONT_MIN, font_size(settings) + step))
    settings.set("ui.font_pt", size)
    apply(app, settings.get("ui.theme", DEFAULT), size)
    return size
