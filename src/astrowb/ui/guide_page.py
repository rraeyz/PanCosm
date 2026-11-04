"""Guide: the training pages, by category, with search.

Content is Markdown in resources/guide/<language>/NN-category.md: "# Category" on the first line, one
"## Topic" per section. A language without its own file shows the English one, so translating the guide
is adding a folder, like the .ts files for the interface; screenshots are in images/<language>/
(tools/guide_screenshots.py), and the tests require every interface language to be complete.
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QSplitter,
    QTextBrowser,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .workspaces import _title

GUIDE = Path(__file__).resolve().parents[1] / "resources" / "guide"


def load(lang="en"):
    """[(category title, intro, [(topic title, markdown), ...]), ...] in file order."""
    out = []
    for path in sorted((GUIDE / "en").glob("*.md")):
        own = GUIDE / lang / path.name
        text = (own if own.exists() else path).read_text(encoding="utf-8")
        head, *sections = text.split("\n## ")
        title, _, intro = head.removeprefix("# ").partition("\n")
        topics = [(s.split("\n", 1)[0].strip(), "## " + s) for s in sections]
        out.append((title.strip(), intro.strip(), topics))
    return out


class GuidePage(QWidget):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.categories = load(settings.get("ui.language", "en"))
        split = QSplitter(Qt.Horizontal, self)
        left = QWidget(self)
        ll = QVBoxLayout(left)
        ll.addWidget(_title(self.tr("Guide"), self))
        self.search = QLineEdit(self)
        self.search.setPlaceholderText(self.tr("Search the guide…"))
        self.search.setClearButtonEnabled(True)
        self.search.setToolTip(self.tr("Shows only the guide sections that contain these words"))
        self.search.textChanged.connect(self.filter)
        ll.addWidget(self.search)
        self.tree = QTreeWidget(self)
        self.tree.setHeaderHidden(True)
        self.tree.currentItemChanged.connect(self._show)
        ll.addWidget(self.tree, 1)
        self.count = QLabel(self)
        self.count.setProperty("muted", True)
        ll.addWidget(self.count)
        split.addWidget(left)
        self.text = QTextBrowser(self)
        self.text.setOpenExternalLinks(True)
        self.text.setSearchPaths([str(GUIDE)])  # images/… in the Markdown
        self.text.document().setDocumentMargin(18)
        split.addWidget(self.text)
        split.setSizes([300, 900])
        QVBoxLayout(self).addWidget(split)
        for title, intro, topics in self.categories:
            cat = QTreeWidgetItem(self.tree, [title])
            cat.setData(0, Qt.UserRole, f"# {title}\n\n{intro}\n\n" + "\n\n".join(md for _, md in topics))
            for name, md in topics:
                QTreeWidgetItem(cat, [name]).setData(0, Qt.UserRole, md)
        self.tree.setCurrentItem(self.tree.topLevelItem(0))

    def _show(self, item, _previous=None):
        if item is not None:
            self.text.setMarkdown(item.data(0, Qt.UserRole))

    def filter(self, query):
        """Show only the topics containing every word of the query (and their categories)."""
        words = query.lower().split()
        hits = 0
        for i in range(self.tree.topLevelItemCount()):
            cat = self.tree.topLevelItem(i)
            shown = 0
            for j in range(cat.childCount()):
                topic = cat.child(j)
                text = topic.data(0, Qt.UserRole).lower()
                match = all(w in text for w in words)
                topic.setHidden(not match)
                shown += match
            cat.setHidden(shown == 0)
            cat.setExpanded(bool(words) and shown > 0)
            hits += shown
        self.count.setText(self.tr("{n} topics found").format(n=hits) if words else "")
        first = next(
            (
                self.tree.topLevelItem(i).child(j)
                for i in range(self.tree.topLevelItemCount())
                for j in range(self.tree.topLevelItem(i).childCount())
                if not self.tree.topLevelItem(i).child(j).isHidden()
            ),
            None,
        )
        if words and first is not None:
            self.tree.setCurrentItem(first)
        return hits
