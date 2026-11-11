"""Help beside the work (plans/interface.md UI-7): the guide's paragraph for what is in focus, in a panel at the
right of an area window, with "Open the full guide".

    panel = HelpPanel(); panel.show_anchor("photometry-apertures")
    anchor_for(widget)      # the help anchor of the widget or of the nearest section / stage around it
"""

from PySide6.QtCore import QCoreApplication, Qt, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QTextBrowser, QVBoxLayout, QWidget

translate = QCoreApplication.translate


def anchor_for(widget):
    """The "help_anchor" property of the widget or of its nearest parent that has one, else None."""
    while widget is not None:
        anchor = widget.property("help_anchor")
        if anchor:
            return anchor
        widget = widget.parentWidget()
    return None


class HelpPanel(QWidget):
    full_guide = Signal(str)  # the anchor shown: open the whole guide there

    def __init__(self, lang="en", parent=None):
        super().__init__(parent)
        from ..guide_page import GUIDE

        self.lang, self.anchor = lang, None
        lay = QVBoxLayout(self)
        self.title = QLabel(self)
        self.text = QTextBrowser(self)
        self.text.setOpenExternalLinks(True)
        self.text.setSearchPaths([str(GUIDE)])
        self.more = QPushButton(self.tr("Open the full guide"), self)
        self.more.clicked.connect(lambda: self.full_guide.emit(self.anchor or ""))
        lay.addWidget(self.title)
        lay.addWidget(self.text, 1)
        lay.addWidget(self.more)

    def show_anchor(self, anchor):
        """Show the topic; False (and a short note) when the anchor names no topic."""
        from ..guide_page import anchors

        found = anchors(self.lang).get(anchor)
        self.anchor = anchor if found else None
        if found is None:
            self.title.setText("")
            self.text.setPlainText(self.tr("There is no guide paragraph for this yet."))
            return False
        category, name, md = found
        self.title.setText(f"<b>{name}</b><br><span style='color:gray'>{category}</span>")
        self.text.setMarkdown(md.split("\n", 1)[1] if md.startswith("## ") else md)
        return True


def open_help(widget, anchor):
    """Show the guide topic for a widget's window: its Help panel (area windows), else the guide page."""
    win = widget.window()
    if hasattr(win, "show_help") and win.show_help(anchor):
        return True
    for candidate in (win, win.parentWidget()):  # the main window, or the area window's parent (the main window)
        if candidate is not None and hasattr(candidate, "_help_for"):
            candidate._help_for(anchor)
            return True
    return False


def help_line(text, anchor, parent):
    """One short muted line with "More…" opening the guide topic: the long explanation lives in the guide."""
    more = translate("HelpPanel", "More…")  # not inside the f-string: lupdate would not find it there
    label = QLabel(f'{text} <a href="{anchor}">{more}</a>', parent)
    label.setWordWrap(True)
    label.setProperty("muted", True)
    label.setTextFormat(Qt.RichText)
    label.linkActivated.connect(lambda a: open_help(label, a))
    return label
