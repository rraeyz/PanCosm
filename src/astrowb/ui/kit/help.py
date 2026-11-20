"""Help beside the work (plans/interface.md UI-7): the guide's paragraph for what is in focus, in a panel at the
right of an area window, with "Open the full guide".

    panel = HelpPanel(); panel.show_anchor("photometry-apertures")
    anchor_for(widget)      # the help anchor of the widget or of the nearest section / stage around it
"""

from PySide6.QtCore import QCoreApplication, Qt, Signal
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

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
        self.search = QLineEdit(self)
        self.search.setPlaceholderText(self.tr("Search the guide"))
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.find)
        self.links = QListWidget(self)  # the search's hits, or the related topics when nothing is typed
        self.links.setMaximumHeight(110)
        self.links.itemActivated.connect(lambda item: self.show_anchor(item.data(Qt.UserRole)))
        self.links.itemClicked.connect(lambda item: self.show_anchor(item.data(Qt.UserRole)))
        self.related = QLabel(self)
        self.title = QLabel(self)
        self.text = QTextBrowser(self)
        self.text.setOpenExternalLinks(True)
        self.text.setSearchPaths([str(GUIDE)])
        self.more = QPushButton(self.tr("Open the full guide"), self)
        self.more.clicked.connect(lambda: self.full_guide.emit(self.anchor or ""))
        lay.addWidget(self.search)
        lay.addWidget(self.title)
        lay.addWidget(self.text, 1)
        lay.addWidget(self.related)
        lay.addWidget(self.links)
        lay.addWidget(self.more)

    def _list(self, found):
        """[(anchor, title)] in the list under the text, at most six."""
        self.links.clear()
        for anchor, name in found[:6]:
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, anchor)
            self.links.addItem(item)
        self.links.setVisible(bool(found))
        return [a for a, _n in found[:6]]

    def find(self, query):
        """Topics whose title or text has every word of the query; with no query, the related ones."""
        from ..guide_page import anchors

        words = query.casefold().split()
        table = anchors(self.lang)
        if not words:
            self.related.setText(self.tr("Related"))
            here = table.get(self.anchor)
            same = [(a, n) for a, (c, n, _m) in table.items() if here and c == here[0] and a != self.anchor]
            return self._list(same)
        self.related.setText(self.tr("Found"))
        hits = [(a, n) for a, (_c, n, md) in table.items() if all(w in f"{n} {md}".casefold() for w in words)]
        return self._list(hits)

    def show_anchor(self, anchor):
        """Show the topic; False (and a short note) when the anchor names no topic."""
        from ..guide_page import anchors

        found = anchors(self.lang).get(anchor)
        self.anchor = anchor if found else None
        if found is None:
            self.title.setText("")
            self.text.setPlainText(self.tr("There is no guide paragraph for this yet."))
            self.find(self.search.text())
            return False
        category, name, md = found
        self.title.setText(f"<b>{name}</b><br><span style='color:gray'>{category}</span>")
        self.text.setMarkdown(md.split("\n", 1)[1] if md.startswith("## ") else md)
        self.find(self.search.text())  # the related topics, or still the search's hits
        return True


def coach_mark(window, stage):
    """A small dismissible hint at the top of a stage the first time it is opened (UI-7 item 5). It is remembered
    as seen when shown; Settings → General → Hints turns them all off. Returns the banner or None."""
    seen = window.settings.get("ui.hints_seen", [])
    mark, panel = f"{window.key}.{stage.key}", window.stage_panels[stage.key]
    if not stage.hint or mark in seen or not window.settings.get("ui.hints", True):
        return None
    from .banners import InfoBanner

    banner = InfoBanner("info", stage.hint, parent=panel)
    panel.body.insertWidget(0, banner)
    window.settings.set("ui.hints_seen", [*seen, mark])
    return banner


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


class WhatsThis:
    """Shift+F1 (UI-7): the pointer becomes a question mark; the next click on a control opens its guide topic (as
    F1 does for the control in focus) instead of acting; Esc ends it without a topic."""

    def __init__(self, window):
        from PySide6.QtCore import QObject, Qt
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtWidgets import QApplication

        self.window = window

        class Filter(QObject):
            def eventFilter(inner, obj, event):  # noqa: N805
                from PySide6.QtCore import QEvent

                if event.type() == QEvent.MouseButtonPress and hasattr(obj, "mapTo"):
                    self.end()
                    window.help_for_widget(obj)
                    return True
                if event.type() == QEvent.KeyPress and event.key() == Qt.Key_Escape:
                    self.end()
                    return True
                return False

        self.filter = Filter(window)
        QApplication.instance().installEventFilter(self.filter)
        QGuiApplication.setOverrideCursor(Qt.WhatsThisCursor)

    def end(self):
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtWidgets import QApplication

        QApplication.instance().removeEventFilter(self.filter)
        QGuiApplication.restoreOverrideCursor()
