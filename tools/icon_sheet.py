"""Contact sheet of every icon kind at 16, 20, 24 and 32 px in the dark and light themes (plans/interface.md UI-2),
to look at before an icon is accepted.

    python tools/icon_sheet.py [docs/design/icons.png]
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtCore import QRect, Qt  # noqa: E402
from PySide6.QtGui import QColor, QPainter, QPalette, QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from astrowb.ui.kit import tokens  # noqa: E402
from astrowb.ui.kit.icons import ICONS, icon  # noqa: E402

SIZES = (16, 20, 24, 32)
LABEL, CELL, ROW = 130, 40, 40


def sheet(path):
    app = QApplication.instance() or QApplication([])  # noqa: F841
    kinds = sorted(ICONS)
    half = LABEL + CELL * len(SIZES)
    out = QPixmap(2 * half, ROW * len(kinds))
    painter = QPainter(out)
    for column, name in enumerate(("dark", "light")):
        colours = tokens.THEMES[name]
        widget = QWidget()
        pal = widget.palette()
        pal.setColor(QPalette.WindowText, QColor(colours["text"]))
        pal.setColor(QPalette.PlaceholderText, QColor(colours["text.faint"]))
        pal.setColor(QPalette.Highlight, QColor(colours["accent"]))
        widget.setPalette(pal)
        x0 = column * half
        painter.fillRect(x0, 0, half, out.height(), QColor(colours["surface.0"]))
        painter.setPen(QColor(colours["text.muted"]))
        for row, kind in enumerate(kinds):
            y = row * ROW
            painter.drawText(QRect(x0 + 6, y, LABEL - 6, ROW), Qt.AlignVCenter, kind)
            for i, size in enumerate(SIZES):
                x = x0 + LABEL + i * CELL + (CELL - size) // 2
                painter.drawPixmap(x, y + (ROW - size) // 2, icon(kind, widget, size).pixmap(size, size))
    painter.end()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    out.save(str(path))
    return path


if __name__ == "__main__":
    print(sheet(sys.argv[1] if len(sys.argv) > 1 else "docs/design/icons.png"))
