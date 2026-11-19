"""A click on an O−C point selects its row of the minima table, and a selected row rings its point (UI-16.5, OC-W).
The points' ids are the minima's times, which the table's Time column holds too: rows may be sorted or unticked."""


def _time(table, r):
    try:
        return float(table.item(r, 1).text())
    except (AttributeError, ValueError):  # an empty or half-typed cell
        return None


def _row_of(table, time):
    return next((r for r in range(table.rowCount()) if _time(table, r) == float(time)), None)


def connect(page):
    table = page.minima_input

    def clicked(name, time):
        r = _row_of(table, time)
        if r is not None:
            table.selectRow(r)
            table.scrollToItem(table.item(r, 1))

    def ring():
        times = {_time(table, r) for r in {i.row() for i in table.selectedItems()}} - {None}
        for s in page.plot.figure.panels[0].series if page.plot.figure.panels else []:
            if s.pickable:
                page.plot.highlight(s.name, [t for t in (s.ids if s.ids is not None else []) if t in times])

    page.plot.point_clicked.connect(clicked)
    table.itemSelectionChanged.connect(ring)
