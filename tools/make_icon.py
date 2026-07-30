"""Draw the placeholder application icon (512 px PNG) into the brand folder."""

import sys
from pathlib import Path

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QBrush, QColor, QGuiApplication, QImage, QPainter, QPen, QRadialGradient

out = Path(__file__).resolve().parents[1] / "src/astrowb/resources/brand/icon.png"
app = QGuiApplication(sys.argv)
img = QImage(512, 512, QImage.Format_ARGB32)
img.fill(Qt.transparent)
p = QPainter(img)
p.setRenderHint(QPainter.Antialiasing)
g = QRadialGradient(QPointF(256, 256), 250)
g.setColorAt(0, QColor("#1d3b6e"))
g.setColorAt(1, QColor("#070d1c"))
p.setBrush(QBrush(g))
p.setPen(Qt.NoPen)
p.drawRoundedRect(16, 16, 480, 480, 96, 96)
p.setPen(QPen(QColor("#8fb8ff"), 14))
p.setBrush(Qt.NoBrush)
p.drawEllipse(QPointF(256, 256), 170, 70)  # orbit
p.setPen(Qt.NoPen)
p.setBrush(QColor("#ffd36b"))
p.drawEllipse(QPointF(256, 256), 62, 62)  # star
p.setBrush(QColor("#ffffff"))
p.drawEllipse(QPointF(410, 220), 20, 20)  # companion
p.end()
img.save(str(out))
print(out)
