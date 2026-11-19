"""UI-16.5 / OC-W: leave O−C points out and bring them back from the diagram; synthetic minima."""

from PySide6.QtCore import Qt

from astrowb.ui.oc_page import OCPage

T0, P = 2455000.0, 2.5
TIMES = [T0 + P * k + 0.0003 * (-1) ** k for k in range(10)]


def _page(qtbot):
    page = OCPage()
    qtbot.addWidget(page)
    page.text.setPlainText("\n".join(f"{t!r} 0.001 I" for t in TIMES))
    page.period.setText(str(P))
    page.run_fit()
    return page


def _use(page):
    t = page.minima_input
    return [t.item(r, 0).checkState() == Qt.Checked for r in range(t.rowCount())]


def test_leave_out_and_bring_back_two_selected_points(qtbot):
    page = _page(qtbot)
    t = page.minima_input
    assert len(page.fit_minima) == 10
    t.sortItems(1, Qt.DescendingOrder)  # rows moved: the time finds the row
    times = [TIMES[2], TIMES[5]]
    page.plot.point_clicked.emit("primary", times[0])
    page.plot.points_selected.emit("primary", [times[1]])  # a lasso adds to the click
    page.leave_out_button.click()
    assert sum(_use(page)) == 8 and len(page.fit_minima) == 8
    left = next(s for s in page.plot.figure.panels[0].series if s.name == "left out")
    assert sorted(left.ids) == times and left.pickable
    page.undo_stack.undo()
    assert all(_use(page)) and len(page.fit_minima) == 10
    page.undo_stack.redo()
    assert len(page.fit_minima) == 8
    page.plot.points_selected.emit("left out", times)  # the grey points, selected the same way
    page.bring_back_button.click()
    assert all(_use(page)) and len(page.fit_minima) == 10
    assert not any(s.name == "left out" for s in page.plot.figure.panels[0].series)


def test_delete_key_leaves_the_selected_out(qtbot):
    page = _page(qtbot)
    page.plot.point_clicked.emit("primary", TIMES[3])
    page.plot.key_pressed.emit("delete", None)
    assert sum(_use(page)) == 9 and len(page.fit_minima) == 9
