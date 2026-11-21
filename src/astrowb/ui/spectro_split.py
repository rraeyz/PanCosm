"""A job's whole column split into stages along its own widgets (plans/interface.md UI-16.3)."""

from .stage_boxes import boxes_from_column


def split_job(whole, picks):
    """picks: [(item number in the column's layout, key, title)]; each stage holds the items from its pick up to the
    next. Returns {key: (title, box)}; nothing is removed or re-created."""
    lay = whole.layout()
    boxes = boxes_from_column(lay, [(key, lay.itemAt(i).widget()) for i, key, _ in picks])
    return {key: (title, boxes[key]) for _, key, title in picks}
