"""A table and a plot that show the same rows select together (ARC-8 item 3): rows selected in the table are ringed
in the plot; a point clicked or lassoed in the plot selects its row. The plot series' ids are the table's row
indices."""

from PySide6.QtCore import QItemSelection, QItemSelectionModel


def link(table_view, plot_view, series):
    """Keep table_view (kit.table.TableView) and plot_view (plot.view.PlotView, series `series`) selecting together."""
    busy = [False]

    def table_changed(*_):
        if not busy[0]:
            plot_view.highlight(series, table_view.selected_rows())

    def select_rows(rows):
        busy[0] = True
        try:
            position = {int(r): i for i, r in enumerate(table_view.shown_rows())}
            model, sel = table_view.view.model(), QItemSelection()
            for r in rows:
                i = position.get(int(r))
                if i is not None:  # a row the table's filter hides stays unselected there
                    sel.select(model.index(i, 0), model.index(i, model.columnCount() - 1))
            table_view.view.selectionModel().select(sel, QItemSelectionModel.ClearAndSelect)
            if rows and int(rows[0]) in position:
                table_view.view.scrollTo(model.index(position[int(rows[0])], 0))
        finally:
            busy[0] = False
        plot_view.highlight(series, list(rows))

    table_view.view.selectionModel().selectionChanged.connect(table_changed)
    plot_view.point_clicked.connect(lambda name, pid: name == series and select_rows([pid]))
    plot_view.points_selected.connect(lambda name, ids: name == series and select_rows(ids))
    return select_rows
