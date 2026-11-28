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
    page.plot.points_selected.emit("left out", times)  # the hollow points, selected the same way
    page.bring_back_button.click()
    assert all(_use(page)) and len(page.fit_minima) == 10
    assert not any(s.name == "left out" for s in page.plot.figure.panels[0].series)


def test_delete_key_leaves_the_selected_out(qtbot):
    page = _page(qtbot)
    page.plot.point_clicked.emit("primary", TIMES[3])
    page.plot.key_pressed.emit("delete", None)
    assert sum(_use(page)) == 9 and len(page.fit_minima) == 9


def test_left_out_minima_are_a_hollow_series_the_toggle_hides(qtbot, tmp_path):
    from astrowb.ui.plot.toolbar import PlotToolbar

    page = _page(qtbot)
    page.plot.point_clicked.emit("primary", TIMES[4])
    page.leave_out_button.click()
    assert len(page.fit_minima) == 9 and TIMES[4] not in [m.time for m in page.fit_minima]  # the fit excludes it
    left = next(s for s in page.plot.figure.panels[0].series if s.name == "left out")
    assert left.left_out and list(left.ids) == [TIMES[4]]
    item = next(e["item"] for e in page.plot.items if e["spec"].name == "left out")
    assert item.isVisible()
    page.plot.set_show_left_out(False)
    assert not item.isVisible() and len(page.fit_minima) == 9
    page.plot.set_show_left_out(True)
    assert item.isVisible()
    page.plot.set_show_left_out(False)
    toolbar = PlotToolbar(page.plot)
    qtbot.addWidget(toolbar)
    assert toolbar.export_publication(str(tmp_path / "oc.pdf"))  # written without the hidden points (publish test)
