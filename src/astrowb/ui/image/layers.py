"""Plain-spec overlay items (ARC-7 item 3): engine code can describe what to draw without Qt; the viewer turns the
specs into graphics items with `build`. Coordinates are 0-based array (x, y), y up, sizes in image pixels, or in
screen pixels when `fixed` (a marker that keeps its size at any zoom)."""

from dataclasses import dataclass

from ..kit.tokens import role


@dataclass
class Item:
    colour: str = role("check")
    width: float = 1.0
    label: str = ""
    id: str = ""
    pickable: bool = False  # kept on the item (data role 2); what a click does with it is the window's business
    fixed: bool = False  # size in screen pixels (Circle, Annulus, Ellipse, Box, Cross)


@dataclass
class Circle(Item):
    x: float = 0.0
    y: float = 0.0
    r: float = 5.0


@dataclass
class Annulus(Item):
    x: float = 0.0
    y: float = 0.0
    r_in: float = 5.0
    r_out: float = 8.0


@dataclass
class Ellipse(Item):
    x: float = 0.0
    y: float = 0.0
    a: float = 5.0  # semi-axis along the angle
    b: float = 3.0
    angle: float = 0.0  # degrees, counter-clockwise from +x in array coordinates


@dataclass
class Box(Item):
    x0: float = 0.0
    y0: float = 0.0
    x1: float = 1.0
    y1: float = 1.0


@dataclass
class Polyline(Item):
    points: tuple = ()  # ((x, y), ...)


@dataclass
class Text(Item):
    x: float = 0.0
    y: float = 0.0
    text: str = ""


@dataclass
class Cross(Item):
    x: float = 0.0
    y: float = 0.0
    r: float = 6.0


def build(specs, to_scene):
    """Graphics items for the specs; to_scene(x, y) maps array to scene coordinates (the viewer's)."""
    from PySide6.QtGui import QColor, QPainterPath, QPen, QTransform
    from PySide6.QtWidgets import QGraphicsItem, QGraphicsPathItem, QGraphicsSimpleTextItem

    items = []
    for s in specs:
        if isinstance(s, Text):
            item = QGraphicsSimpleTextItem(s.text)
            item.setBrush(QColor(s.colour))
            item.setPos(*to_scene(s.x, s.y))
            item.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        else:
            path = QPainterPath()
            if isinstance(s, Polyline):
                if not s.points:
                    continue
                path.moveTo(*to_scene(*s.points[0]))
                for x, y in s.points[1:]:
                    path.lineTo(*to_scene(x, y))
                cx, cy = 0.0, 0.0
            else:
                if isinstance(s, Box):
                    (x0, y0), (x1, y1) = to_scene(s.x0, s.y0), to_scene(s.x1, s.y1)
                    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
                    path.addRect(-abs(x1 - x0) / 2, -abs(y1 - y0) / 2, abs(x1 - x0), abs(y1 - y0))
                else:
                    cx, cy = to_scene(s.x, s.y)
                    if isinstance(s, Circle):
                        path.addEllipse(-s.r, -s.r, 2 * s.r, 2 * s.r)
                    elif isinstance(s, Annulus):
                        path.addEllipse(-s.r_in, -s.r_in, 2 * s.r_in, 2 * s.r_in)
                        path.addEllipse(-s.r_out, -s.r_out, 2 * s.r_out, 2 * s.r_out)
                    elif isinstance(s, Ellipse):
                        path.addEllipse(-s.a, -s.b, 2 * s.a, 2 * s.b)
                    else:  # Cross
                        path.moveTo(-s.r, 0)
                        path.lineTo(s.r, 0)
                        path.moveTo(0, -s.r)
                        path.lineTo(0, s.r)
            item = QGraphicsPathItem(path)
            pen = QPen(QColor(s.colour))
            pen.setWidthF(s.width)
            pen.setCosmetic(True)
            item.setPen(pen)
            if not isinstance(s, Polyline):
                item.setPos(cx, cy)
            if isinstance(s, Ellipse):
                item.setTransform(QTransform().rotate(-s.angle))  # y is down in the scene
            if s.fixed and not isinstance(s, Polyline):
                item.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        item.setToolTip(s.label)
        item.setData(1, s.id)
        item.setData(2, s.pickable)
        items.append(item)
    return items
