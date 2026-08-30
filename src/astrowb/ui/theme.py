"""Application look: Fusion style with our own palette and style sheet, applied to every page, tab and
plot. Themes: dark (default, blue-black) and light. A saved theme that no longer exists falls back to dark.
"""

from PySide6.QtGui import QColor, QPalette

THEMES = {
    # window, panel (inputs, lists), raised (buttons, tabs), text, muted text, accent, accent text, border
    "dark": ("#16191f", "#1e232b", "#272d37", "#e6e9ef", "#8b93a3", "#4f8cff", "#ffffff", "#323946"),
    "light": ("#f3f5f8", "#ffffff", "#e8ecf2", "#1b2230", "#5d6778", "#2f6fe4", "#ffffff", "#cfd6e0"),
}
DEFAULT = "dark"


def colors(name):
    keys = ("window", "panel", "raised", "text", "muted", "accent", "accent_text", "border")
    return dict(zip(keys, THEMES.get(name, THEMES[DEFAULT]), strict=True))


def style_sheet(c):
    return f"""
* {{ font-size: 10pt; }}
QWidget {{ color: {c["text"]}; }}
QMainWindow, QDialog {{ background: {c["window"]}; }}
QToolTip {{ background: {c["raised"]}; color: {c["text"]}; border: 1px solid {c["border"]}; padding: 4px; }}
QLabel[muted="true"] {{ color: {c["muted"]}; }}
QListWidget#sidebar {{
    background: {c["panel"]}; border: none; border-right: 1px solid {c["border"]};
    font-size: 11pt; padding: 8px 6px; outline: 0;
}}
QListWidget#sidebar::item {{ padding: 6px 12px; margin: 1px 0; border-radius: 8px; }}
QListWidget#sidebar::item:hover {{ background: {c["raised"]}; }}
QListWidget#sidebar::item:selected {{ background: {c["accent"]}; color: {c["accent_text"]}; }}
QListWidget#sidebar::item:disabled {{
    background: transparent; color: {c["muted"]}; font-size: 8pt; font-weight: bold; padding: 8px 12px 0px 12px;
}}
QPushButton {{
    background: {c["raised"]}; border: 1px solid {c["border"]}; border-radius: 7px;
    padding: 6px 14px; min-height: 18px;
}}
QPushButton:hover {{ border-color: {c["accent"]}; }}
QPushButton:pressed, QPushButton:checked {{ background: {c["accent"]}; color: {c["accent_text"]}; }}
QPushButton:disabled {{ color: {c["muted"]}; border-color: {c["raised"]}; }}
QPushButton:default, QPushButton[primary="true"] {{
    background: {c["accent"]}; color: {c["accent_text"]}; border: none;
}}
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
QGraphicsView {{ background: #000000; border: none; }}
"""


def apply(app, name=DEFAULT):
    """Apply a theme to the whole application (widgets and matplotlib plots)."""
    import matplotlib as mpl

    c = colors(name)
    app.setStyle("Fusion")
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
    pal.setColor(QPalette.Disabled, QPalette.Text, QColor(c["muted"]))
    pal.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(c["muted"]))
    app.setPalette(pal)
    app.setStyleSheet(style_sheet(c))
    mpl.rcParams.update(
        {
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
            "axes.prop_cycle": mpl.cycler(color=[c["accent"], "#ff8a3d", "#3ecf8e", "#e5484d", "#b07cff", "#f5c542"]),
        }
    )
    return c
