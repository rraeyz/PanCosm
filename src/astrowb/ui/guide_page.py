"""Guide: the training pages, by category, with search.

Content is Markdown in resources/guide/<language>/NN-category.md: "# Category" on the first line, one
"## Topic" per section. A language without its own file shows the English one, so translating the guide
is adding a folder, like the .ts files for the interface; screenshots are in images/<language>/
(tools/guide_screenshots.py), and the tests require every interface language to be complete.
"""

import re
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


ANCHOR = re.compile(r"\s*\{#([a-z0-9-]+)\}\s*$")


def load(lang="en"):
    """[(category title, intro, [(topic title, markdown), ...]), ...] in file order. A topic's heading may end in a
    stable anchor "{#photometry-apertures}" (the same in every language); it is taken off here (anchors())."""
    return [(title, intro, [(name, md) for name, md, _a in topics]) for title, intro, topics in _parse(lang)]


def anchors(lang="en"):
    """{anchor: (category title, topic title, markdown)}; a topic not yet translated comes from English."""
    out = {}
    for code in ("en", lang) if lang != "en" else ("en",):
        for title, _intro, topics in _parse(code):
            out.update({a: (title, name, md) for name, md, a in topics if a})
    return out


def _parse(lang):
    out = []
    for path in sorted((GUIDE / "en").glob("*.md")):
        own = GUIDE / lang / path.name
        text = (own if own.exists() else path).read_text(encoding="utf-8")
        head, *sections = text.split("\n## ")
        title, _, intro = head.removeprefix("# ").partition("\n")
        topics = []
        for s in sections:
            first, _, body = s.partition("\n")
            m = ANCHOR.search(first)
            name = ANCHOR.sub("", first).strip()
            topics.append((name, f"## {name}\n{body}", m.group(1) if m else None))
        out.append((title.strip(), intro.strip(), topics))
    return out


class GuidePage(QWidget):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.lang = settings.get("ui.language", "en")
        self.categories = load(self.lang)
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
        self.items = {}  # anchor -> tree item
        for title, intro, topics in _parse(self.lang):
            cat = QTreeWidgetItem(self.tree, [title])
            cat.setData(0, Qt.UserRole, f"# {title}\n\n{intro}\n\n" + "\n\n".join(md for _, md, _a in topics))
            for name, md, anchor in topics:
                item = QTreeWidgetItem(cat, [name])
                item.setData(0, Qt.UserRole, md)
                if anchor:
                    self.items[anchor] = item
        self.tree.setCurrentItem(self.tree.topLevelItem(0))

    def show_anchor(self, anchor):
        """Open the topic with this anchor (False when there is none: the anchor is wrong or not yet written)."""
        item = self.items.get(anchor)
        if item is None:
            found = anchors(self.lang).get(anchor)
            if found is None:
                return False
            self.text.setMarkdown(found[2])  # a topic this language has not translated yet: the English one
            return True
        self.search.clear()
        self.tree.setCurrentItem(item)
        return True

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
