"""ARC-6: the plot description, decimation, and the view's mouse and keyboard driven through QTest."""

import numpy as np
import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtTest import QTest

from astrowb.ui.plot import spec as S
from astrowb.ui.plot.spec import AxisSpec, FigureSpec, PanelSpec, SeriesSpec


def test_line_decimation_keeps_every_peak_and_is_exact_when_few():
    x = np.linspace(0, 100, 1_000_000)
    y = np.zeros_like(x)
    y[123_457], y[876_543] = 5.0, -3.0  # single-sample spikes
    xs, ys = S.decimate_line(x, y, 0, 100, 1000)
    assert len(xs) <= 2000 and ys.max() == 5.0 and ys.min() == -3.0 and np.all(np.diff(xs) >= 0)
    xs, ys = S.decimate_line(x, y, 10, 10.001, 1000)  # zoomed in: the real points (and one beyond each edge)
    assert np.array_equal(xs, x[(x >= xs[0]) & (x <= xs[-1])])


def test_point_decimation_keeps_one_real_point_per_pixel():
    rng = np.random.default_rng(1)
    x, y = rng.uniform(0, 1, 200_000), rng.uniform(0, 1, 200_000)
    keep = S.decimate_points(x, y, 0, 1, 0, 1, 100, 100)
    assert len(keep) <= 100 * 100 and len(np.unique(keep)) == len(keep)
    assert len(S.decimate_points(x[:1000], y[:1000], 0, 1, 0, 1, 100, 100)) == 1000


def test_time_offset_and_axis_title():
    axis = AxisSpec("BJD", "d", time="bjd")
    off = S.time_offset(np.array([2460512.3, 2460513.1]), axis)
    assert off == 2460000 and axis.title(off) == "BJD − 2460000 [d]"
    assert S.time_offset(np.array([0.1, 0.9]), AxisSpec("phase", time="phase")) == 0


def test_spec_is_json_ready_and_colours_are_colour_blind_safe():
    fig = FigureSpec(
        [PanelSpec(AxisSpec("t"), AxisSpec("m"), [SeriesSpec("a", [1, 2], [3, 4]), SeriesSpec("b", [1], [2])])]
    )
    assert fig.to_dict()["panels"][0]["series"][0]["x"] == [1, 2]
    assert list(fig.colours().values()) == list(S.OKABE_ITO[:2])
    with pytest.raises(ValueError):
        SeriesSpec("c", [1], [1], kind="pie")


def light_curve(n=2000):
    t = 2460512.0 + np.linspace(0, 0.3, n)
    mag = 0.01 * np.sin(t * 50)
    series = SeriesSpec("V", t, mag, yerr=np.full(n, 0.002), pickable=True, ids=np.arange(n) + 100)
    model = SeriesSpec("model", t, mag, kind="line")
    top = PanelSpec(AxisSpec("BJD", "d", time="bjd"), AxisSpec("Δmag", invert=True), [series, model])
    bottom = PanelSpec(AxisSpec("BJD", "d", time="bjd"), AxisSpec("O−C"), [SeriesSpec("res", t, mag * 0)])
    return FigureSpec([top, bottom], title="test")


@pytest.fixture
def view(qapp):
    from astrowb.ui.plot.view import PlotView

    v = PlotView(light_curve())
    v.resize(800, 600)
    v.show()
    QTest.qWaitForWindowExposed(v)
    yield v
    v.close()


def screen_of(view, panel, x, y):
    """Viewport position of the data point (x, y) of a panel (x without the time offset)."""
    vb = view.plots[panel].getViewBox()
    scene = vb.mapViewToScene(QPointF(x, y))
    return view.graphics.mapFromScene(scene)


def move(port, pos, button=Qt.LeftButton):
    """A mouse move with the button held (QTest.mouseMove does not carry it on every platform), spaced like a real
    mouse: pyqtgraph drops moves that come faster than its frame rate."""
    QTest.qWait(20)
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtWidgets import QApplication

    pos = QPointF(pos)
    ev = QMouseEvent(QEvent.MouseMove, pos, port.mapToGlobal(pos), Qt.NoButton, button, Qt.NoModifier)
    QApplication.sendEvent(port, ev)


def drag_path(view, points, button=Qt.LeftButton):
    port = view.graphics.viewport()
    QTest.mousePress(port, button, Qt.NoModifier, points[0])
    for a, b in zip(points, points[1:], strict=False):
        for k in range(1, 6):
            move(port, a + (b - a) * k / 5, button)
    QTest.mouseRelease(port, button, Qt.NoModifier, points[-1])


def drag(view, start, end, button=Qt.LeftButton):
    drag_path(view, [start, end], button)


def test_view_draws_panels_linked_with_offset_and_inverted_axis(view):
    assert len(view.plots) == 2 and view.offsets[id(view.plots[0].getViewBox())] == 2460000
    assert view.plots[0].getViewBox().state["yInverted"]
    view.plots[0].getViewBox().setXRange(512.1, 512.2, padding=0)
    assert view.plots[1].getViewBox().viewRange()[0] == pytest.approx([512.1, 512.2], abs=0.005)


def test_keys_show_all_and_range_selection(view):
    vb = view.plots[0].getViewBox()
    vb.setXRange(512.1, 512.12, padding=0)
    QTest.keyClick(view, Qt.Key_A)
    QTest.qWait(50)
    assert vb.viewRange()[0][1] - vb.viewRange()[0][0] > 0.25
    got = []
    view.range_selected.connect(lambda a, b: got.append((a, b)))
    QTest.keyPress(view, Qt.Key_R)
    drag(view, screen_of(view, 0, 512.05, 0), screen_of(view, 0, 512.15, 0))
    QTest.keyRelease(view, Qt.Key_R)
    assert (
        got
        and got[-1][0] == pytest.approx(2460512.05, abs=0.005)
        and got[-1][1] == pytest.approx(2460512.15, abs=0.005)
    )


def test_a_click_a_few_pixels_off_a_point_still_picks_it(view):
    """The tolerance is in screen pixels: 3 px off picks the nearest point, 30 px off nothing."""
    pts = SeriesSpec("p", [1.0, 5.0, 9.0], [1.0, 3.0, 2.0], pickable=True, ids=[10, 20, 30])
    view.set_figure(FigureSpec([PanelSpec(AxisSpec("x"), AxisSpec("y"), [pts])]))
    clicked = []
    view.point_clicked.connect(lambda name, pid: clicked.append((name, pid)))
    p, port = screen_of(view, 0, 5.0, 3.0), view.graphics.viewport()
    QTest.mouseClick(port, Qt.LeftButton, Qt.NoModifier, p + QPoint(3, 3))
    assert clicked == [("p", 20)]
    QTest.mouseClick(port, Qt.LeftButton, Qt.NoModifier, p + QPoint(0, 30))
    assert clicked == [("p", 20)]


def test_click_lasso_and_cursor_readout(view):
    e = view.items[0]
    i = 700
    clicked, lassoed, read = [], [], []
    view.point_clicked.connect(lambda name, pid: clicked.append((name, pid)))
    view.points_selected.connect(lambda name, ids: lassoed.append((name, ids)))
    view.cursor_moved.connect(read.append)
    p = screen_of(view, 0, e["x"][i], e["y"][i])
    QTest.mouseMove(view.graphics.viewport(), p)
    QTest.mouseClick(view.graphics.viewport(), Qt.LeftButton, Qt.NoModifier, p)
    assert clicked and clicked[-1][0] == "V" and abs(clicked[-1][1] - (100 + i)) < 5
    assert read and "V #" in read[-1]
    QTest.keyPress(view, Qt.Key_L)
    x0, x1 = e["x"][600], e["x"][800]
    lo, hi = (0.98 * v for v in view.plots[0].getViewBox().viewRange()[1])  # just inside the view
    corners = [screen_of(view, 0, x, y) for x, y in ((x0, lo), (x1, lo), (x1, hi), (x0, hi), (x0, lo))]
    drag_path(view, corners)
    QTest.keyRelease(view, Qt.Key_L)
    name, ids = lassoed[-1]
    assert name == "V" and 190 <= len(ids) <= 210 and min(ids) >= 100 + 595


def wheel(view, pos, modifiers):
    from PySide6.QtGui import QWheelEvent
    from PySide6.QtWidgets import QApplication

    port = view.graphics.viewport()
    ev = QWheelEvent(QPointF(pos), QPointF(port.mapToGlobal(pos)), QPoint(), QPoint(0, 120), Qt.NoButton,
                     modifiers, Qt.NoScrollPhase, False)  # fmt: skip
    QApplication.sendEvent(port, ev)


def test_wheel_modifiers_choose_the_axis_and_z_drag_zooms_a_box(view):
    vb = view.plots[0].getViewBox()
    (x0, x1), (y0, y1) = vb.viewRange()
    centre = screen_of(view, 0, (x0 + x1) / 2, (y0 + y1) / 2)
    wheel(view, centre, Qt.ControlModifier)
    (a, b), (c, d) = vb.viewRange()
    assert b - a < x1 - x0 and (c, d) == pytest.approx((y0, y1))
    wheel(view, centre, Qt.ShiftModifier)
    (a2, b2), (c2, d2) = vb.viewRange()
    assert (a2, b2) == pytest.approx((a, b)) and d2 - c2 < d - c
    QTest.keyClick(view, Qt.Key_A)
    QTest.keyPress(view, Qt.Key_Z)
    drag(view, screen_of(view, 0, 512.1, -0.005), screen_of(view, 0, 512.15, 0.005))
    QTest.keyRelease(view, Qt.Key_Z)
    (a, b), _ = vb.viewRange()
    assert a == pytest.approx(512.1, abs=0.01) and b == pytest.approx(512.15, abs=0.01)
    assert view.mode == "pan"


def test_a_million_points_are_decimated(qapp):
    from astrowb.ui.plot.view import PlotView

    t = np.linspace(0, 80, 1_000_000)
    v = PlotView(FigureSpec([PanelSpec(AxisSpec("t"), AxisSpec("f"), [SeriesSpec("tess", t, np.sin(t))])]))
    v.resize(800, 400)
    v.show()
    QTest.qWaitForWindowExposed(v)
    v.plots[0].getViewBox().setXRange(0, 80, padding=0)
    assert len(v.items[0]["shown"]) <= 800 * 400 and len(v.items[0]["shown"]) < 1_000_000
    v.close()


def test_publication_figure_matches_the_spec(tmp_path):
    from astrowb.ui.plot import publish as P

    spec = light_curve(500)
    spec.panels[0].x.limits = (2460512.05, 2460512.25)
    fig = P.figure(spec, "aas", "single")
    top, bottom = fig.axes
    assert top.get_xlim() == pytest.approx((512.05, 512.25)) and top.yaxis_inverted()
    assert top.get_ylabel() == "Δmag" and bottom.get_xlabel() == "BJD − 2460000 [d]"
    drawn = {line.get_label(): len(line.get_xdata()) for line in top.get_lines()}
    assert drawn["V"] == 500 and drawn["model"] == 500
    pdf = P.publish(spec, tmp_path / "lc.pdf")
    data = pdf.read_bytes()
    assert b"/FontFile2" in data  # fonts embedded as TrueType
    box = [float(v) for v in data.split(b"/MediaBox [")[1].split(b"]")[0].split()]
    assert box[2] - box[0] == pytest.approx(3.5 * 72, abs=0.5)  # AAS single column


def test_data_behind_and_the_script_redraw_the_figure(tmp_path):
    import os
    import subprocess
    import sys

    from astrowb.ui.plot import publish as P

    spec = light_curve(50)
    P.data_behind(spec, tmp_path / "lc.ecsv")
    P.script(spec, tmp_path / "lc.py", tmp_path / "lc.ecsv")
    env = {**os.environ, "MPLBACKEND": "Agg"}
    subprocess.run([sys.executable, "lc.py"], cwd=tmp_path, env=env, check=True, timeout=120)
    assert (tmp_path / "lc.pdf").stat().st_size > 1000


def test_time_axis_as_ut_hours_and_phase(view):
    view.original.panels[0].x.period, view.original.panels[0].x.epoch = 0.1, 2460512.0
    view.set_time_mode("phase")
    x = view.items[0]["x"]
    assert x.min() >= 0 and x.max() < 1 and view.plots[0].getAxis("bottom").labelText == "phase"
    assert view.plots[1].getAxis("bottom").labelText.startswith("BJD")  # no period: stays in BJD
    view.set_time_mode("ut")
    assert view.items[0]["x"][0] == pytest.approx(12.0) and view.plots[0].getAxis("bottom").labelText == "UT [h]"
    view.set_time_mode("bjd")
    assert view.offsets[id(view.plots[0].getViewBox())] == 2460000


def test_toolbar_modes_show_all_exports_and_pop_out(view, tmp_path):
    from astrowb.ui.plot.toolbar import PlotToolbar

    bar = PlotToolbar(view)
    zoom, rng = bar.modes.buttons()[1], bar.modes.buttons()[2]
    zoom.click()
    assert view.mode == view.base_mode == "zoom"
    QTest.keyPress(view, Qt.Key_R)
    assert view.mode == "range"
    QTest.keyRelease(view, Qt.Key_R)
    assert view.mode == "zoom"  # a released key returns to the toolbar's mode
    rng.click()
    assert view.mode == "range" and not zoom.isChecked()
    bar.modes.buttons()[0].click()
    assert view.mode == "pan"
    view.plots[0].getViewBox().setRange(xRange=(0.1, 0.2))
    bar.findChildren(type(zoom))[4].click()  # Show all
    assert view.plots[0].getViewBox().viewRange()[0][1] > 0.25
    assert bar.export_data(tmp_path / "d.ecsv") and (tmp_path / "d.ecsv").exists()
    assert bar.export_publication(str(tmp_path / "f.pdf")).endswith("f.pdf") and (tmp_path / "f.pdf").exists()
    window = bar.pop_out()
    assert window.isVisible() and len(window.findChildren(type(view))) == 1
    window.close()


def test_plot_view_says_why_it_is_empty_busy_or_failed(qapp, monkeypatch):
    from astrowb.ui.plot.view import PlotView

    v = PlotView()
    v.resize(500, 300)
    v.show()
    assert v.is_empty() and v.hint.isVisible() and v.hint.text()
    v.set_empty_hint("Choose a star to see its light curve")
    v.set_busy("Working: x")
    assert v.hint.text() == "Working: x"
    v.set_busy(None)
    assert v.hint.text().startswith("Choose a star")
    v.set_figure(light_curve())
    assert not v.is_empty() and not v.hint.isVisible()
    monkeypatch.setattr(v, "_draw_figure", lambda *a: (_ for _ in ()).throw(ValueError("bad axis limits")))
    v.set_figure(light_curve())
    assert v.hint.isVisible() and "bad axis limits" in v.hint.text() and v.failed
    monkeypatch.undo()
    v.set_figure(light_curve())
    assert not v.hint.isVisible() and v.failed is None
    v.close()


def test_plot_view_copy_picture_and_copy_data(view):
    from PySide6.QtWidgets import QApplication

    assert view.copy_data() == 2000 * 2 + 2000 and QApplication.clipboard().text().splitlines()[1].startswith(
        "Δmag\tV\t"
    )
    view.copy_picture()
    assert not QApplication.clipboard().pixmap().isNull()
    names = [a.text() for a in view.plots[0].getViewBox().menu.actions()]
    assert "Copy picture" in names and "Copy data" in names


def test_named_ticks_equal_aspect_and_pieces_of_one_curve(qapp, tmp_path):
    from astrowb.ui.plot import publish as P
    from astrowb.ui.plot.view import PlotView

    pieces = [SeriesSpec("curve", [i, i + 1], [0, 1], kind="line") for i in range(3)]
    spec = FigureSpec(
        [
            PanelSpec(
                AxisSpec("Band", ticks=[(1, "B"), (2, "V")]),
                AxisSpec("y"),
                [SeriesSpec("p", [1, 2], [1, 2]), *pieces],
                equal=True,
            )
        ]
    )
    fig = P.figure(spec)
    ax = fig.axes[0]
    assert [t.get_text() for t in ax.get_xticklabels()] == ["B", "V"] and ax.get_aspect() == 1.0
    assert [t.get_text() for t in ax.get_legend().get_texts()] == ["p", "curve"]
    view = PlotView(spec)
    plot = view.plots[0]
    assert plot.getViewBox().state["aspectLocked"]
    assert plot.getAxis("bottom")._tickLevels[0] == [(1, "B"), (2, "V")]
    assert len(plot.legend.items) == 2


def test_move_vline_moves_the_line_not_the_figure(view):
    spec = FigureSpec(
        [
            PanelSpec(
                AxisSpec("x"), AxisSpec("y"), [SeriesSpec("a", [0, 10], [0, 1]), SeriesSpec("level", [3], kind="vline")]
            )
        ]
    )
    view.set_figure(spec)
    view.move_vline("level", 7.0)
    line = next(e for e in view.items if e["spec"].name == "level")["lines"][0]
    assert line.value() == 7.0 and view.figure.panels[0].series[1].x[0] == 7.0


def test_vlines_sit_right_on_a_log_axis(view):
    spec = FigureSpec(
        [
            PanelSpec(
                AxisSpec("P", scale="log"),
                AxisSpec("y"),
                [SeriesSpec("a", [1, 100], [0, 1]), SeriesSpec("p", [10], kind="vline")],
            )
        ]
    )
    view.set_figure(spec)
    line = next(e for e in view.items if e["spec"].name == "p")["lines"][0]
    assert line.value() == pytest.approx(1.0)  # log10(10)
    view.move_vline("p", 100.0)
    assert line.value() == pytest.approx(2.0)


def test_points_on_a_log_axis_are_drawn_and_clickable_where_they_are(view):
    spec = FigureSpec(
        [
            PanelSpec(
                AxisSpec("P", scale="log"), AxisSpec("y"), [SeriesSpec("p", [1, 10, 100], [1, 2, 3], pickable=True)]
            )
        ]
    )
    view.set_figure(spec)
    item = next(e for e in view.items)["item"]
    assert list(item.getData()[0]) == pytest.approx([0.0, 1.0, 2.0])  # log10 of the periods


def test_text_span_dash_clicks_and_keys_in_both_outputs(view, tmp_path):
    """Rotated labels, shaded x ranges and dotted lines draw on screen and in the publication figure; a click that
    hits no point and a letter key report the data position."""
    from astrowb.ui.plot import publish as P

    spec = FigureSpec(
        [
            PanelSpec(
                AxisSpec("x"),
                AxisSpec("y"),
                [
                    SeriesSpec("a", [0, 10], [0, 1], kind="line", dash="dash"),
                    SeriesSpec("night", [2, 6], [3, 8], kind="span", alpha=0.2, colour="#000080"),
                    SeriesSpec("names", [4, 5], [1, 1], kind="text", labels=["Hα", "Hβ"], angle=90),
                    SeriesSpec("ref", [5.0], kind="vline", dash="dot"),
                ],
            )
        ]
    )
    view.set_figure(spec)
    legend = view.plots[0].legend  # pooled plots keep theirs, hidden
    assert view.failed is None and (legend is None or not legend.isVisible())  # one real series: no legend
    kinds = {e["spec"].name: len(e["lines"]) for e in view.items if "lines" in e}
    assert kinds == {"night": 2, "names": 2, "ref": 1}
    assert view._full_range(view.plots[0].getViewBox(), spec.panels[0])[0] == (0, 10)  # spans count for the range
    ax = P.figure(spec).axes[0]
    assert [t.get_text() for t in ax.texts] == ["Hα", "Hβ"] and ax.texts[0].get_rotation() == 90
    assert len(ax.patches) == 2 and ax.get_legend() is None
    assert ax.get_lines()[0].get_linestyle() == "--"
    got, keys = [], []
    view.plot_clicked.connect(lambda *a: got.append(a))
    view.key_pressed.connect(lambda k, x: keys.append((k, x)))
    QTest.mouseClick(view.graphics.viewport(), Qt.LeftButton, Qt.NoModifier, screen_of(view, 0, 3.0, 0.5))
    assert got and got[-1][0] == 0 and got[-1][1] == pytest.approx(3.0, abs=0.2)
    QTest.qWait(50)  # spaced like a real mouse: pyqtgraph drops a move that comes right after the click
    QTest.mouseMove(view.graphics.viewport(), screen_of(view, 0, 7.0, 0.5))
    QTest.qWait(50)
    QTest.keyClick(view, Qt.Key_W)
    assert keys == [("w", pytest.approx(7.0, abs=0.2))]


def test_measure_two_clicks_and_the_delete_key(view):
    """UI-10 / UI-12: in measure mode (X held, or the toolbar) two clicks report Δx and Δy; Delete is told to the
    page as a key with the cursor's x."""
    view.set_figure(
        FigureSpec([PanelSpec(AxisSpec("x"), AxisSpec("y"), [SeriesSpec("a", [0, 10], [0, 10], kind="line")])])
    )
    got, keys = [], []
    view.measured.connect(lambda dx, dy: got.append((dx, dy)))
    view.key_pressed.connect(lambda k, x: keys.append(k))
    port = view.graphics.viewport()
    QTest.keyPress(view, Qt.Key_X)
    assert view.mode == "measure"
    QTest.mouseClick(port, Qt.LeftButton, Qt.NoModifier, screen_of(view, 0, 2.0, 3.0))
    assert not got  # the first click only sets the start
    QTest.mouseClick(port, Qt.LeftButton, Qt.NoModifier, screen_of(view, 0, 6.0, 5.0))
    assert got and got[0][0] == pytest.approx(4.0, abs=0.2) and got[0][1] == pytest.approx(2.0, abs=0.2)
    QTest.keyRelease(view, Qt.Key_X)
    assert view.mode == view.base_mode
    QTest.keyClick(view, Qt.Key_Delete)
    assert keys == ["delete"]


def test_a_second_x_axis_along_the_top_in_both_outputs(qapp):
    from astrowb.ui.plot import publish as P
    from astrowb.ui.plot.view import PlotView

    top = AxisSpec("Local time", ticks=[(1.5, "a"), (2.5, "b")])
    right = AxisSpec("Airmass", ticks=[(1.2, "3"), (1.8, "2")])
    spec = FigureSpec(
        [PanelSpec(AxisSpec("UT"), AxisSpec("y"), [SeriesSpec("s", [1, 3], [1, 2])], top=top, right=right)]
    )
    ax = P.figure(spec).axes[0]
    sec, sec_y = ax.child_axes
    assert [t.get_text() for t in sec.get_xticklabels()] == ["a", "b"] and sec.get_xlabel() == "Local time"
    assert [t.get_text() for t in sec_y.get_yticklabels()] == ["3", "2"] and sec_y.get_ylabel() == "Airmass"
    view = PlotView(spec)  # held: a view nothing refers to is freed at once, with its plots
    plot = view.plots[0]
    assert plot.getAxis("top").isVisible() and plot.getAxis("top")._tickLevels[0] == [(1.5, "a"), (2.5, "b")]
    assert plot.getAxis("right").isVisible() and plot.getAxis("right")._tickLevels[0] == [(1.2, "3"), (1.8, "2")]


def test_a_series_coloured_by_values_has_a_colour_bar_in_both_outputs(qapp, tmp_path):
    from astrowb.ui.plot import publish as P
    from astrowb.ui.plot.view import PlotView

    order = [30.0, 30.0, 31.0, 32.0]
    spec = FigureSpec(
        [
            PanelSpec(
                AxisSpec("x"),
                AxisSpec("y"),
                [SeriesSpec("res", [1, 2, 3, 4], [1, 2, 3, 4], values=order)],
                colourbar="Order",
            )
        ]
    )
    fig = P.figure(spec)
    assert len(fig.axes) == 2 and fig.axes[1].get_ylabel() == "Order"  # the plot and its colour bar
    assert list(fig.axes[0].collections[0].get_array()) == order
    view = PlotView(spec)
    assert view.colourbars[0].axis.labelText == "Order" and view.colourbars[0].values == (30.0, 32.0)
    brushes = view.items[0]["brushes"]
    assert brushes[0].color() != brushes[3].color() and brushes[0].color() == brushes[1].color()
    P.data_behind(spec, tmp_path / "d.ecsv")
    assert "values" in (tmp_path / "d.ecsv").read_text() and spec.to_dict()["panels"][0]["series"][0]["values"] == order


def test_a_histogram_with_edges_is_drawn(qtbot, caplog):
    from astrowb.ui.plot.view import PlotView

    view = PlotView()
    qtbot.addWidget(view)
    counts, edges = np.histogram(np.random.default_rng(1).normal(size=500), bins=16)  # 17 edges, 16 counts
    hist = SeriesSpec("h", edges, counts, kind="histogram")
    view.set_figure(FigureSpec([PanelSpec(AxisSpec("x"), AxisSpec("n"), [hist])]))
    assert "plot not drawn" not in caplog.text


def _pool_figure(n, flavour):
    def panel(i):
        s = [SeriesSpec("a", [1, 2, 3], [1, 2, 4]), SeriesSpec("b", [1, 2, 3], [2, 3, 5])]
        if flavour == 1:
            return PanelSpec(
                AxisSpec("x", scale="log"), AxisSpec("y", scale="log"), s, top=AxisSpec("t", ticks=[(2, "u")])
            )
        if flavour == 2:
            s = [SeriesSpec("c", [1, 2, 3], [1, 2, 4], values=[1.0, 2.0, 3.0])]
            return PanelSpec(AxisSpec("x"), AxisSpec("y"), s, colourbar="Order", right=AxisSpec("r", ticks=[(2, "v")]))
        return PanelSpec(AxisSpec(f"p{i}"), AxisSpec("q"), s[:1], grid=True)

    return FigureSpec([panel(i) for i in range(n)], shared_x=n > 1, title="T")


def _state(view):
    return [
        (
            p.getAxis("bottom").labelText,
            p.vb.state["logMode"],
            p.legend is not None and p.legend.isVisible(),
            p.getAxis("top").isVisible(),
            p.getAxis("right").isVisible(),
            len(p.items),
            p.titleLabel.isVisible(),
        )
        for p in view.plots
    ] + [len(view.colourbars)]


def test_redraws_reuse_the_pooled_plot_items(qapp):
    from astrowb.ui.plot.view import PlotView

    view = PlotView()
    for i in range(200):
        view.set_figure(_pool_figure((1, 3, 2)[i % 3], i % 3))
    assert len(view._pool) == 3
    view.set_figure(_pool_figure(3, 1))
    view.set_figure(_pool_figure(1, 0))
    fresh = PlotView(_pool_figure(1, 0))
    assert _state(view) == _state(fresh) and len(view.graphics.ci.items) == len(fresh.graphics.ci.items)


def test_qt_owns_the_menus_of_every_plot(qapp):
    from astrowb.ui.plot.view import PlotView

    for i in range(20):
        view = PlotView(_pool_figure(1 + i % 3, i % 3))
        view.set_figure(_pool_figure(3, 1))
        for plot in view._pool:  # pyqtgraph leaves them parentless: freed by Python's GC they corrupted the heap
            assert plot.vb.menu.parent() is view and plot.ctrlMenu.parent() is view
        view.deleteLater()
        qapp.processEvents()


def test_views_are_freed_with_no_teardown_errors(qapp, capfd):
    import gc
    import weakref

    from PySide6.QtCore import QEvent

    from astrowb.ui.plot.view import PlotView

    refs = []
    for i in range(30):
        view = PlotView(_pool_figure(3, 1))
        view.set_figure(_pool_figure(2, 0))
        view.set_figure(_pool_figure(1 + i % 3, i % 3))
        view.show()
        qapp.processEvents()
        refs.append(weakref.ref(view))
        if i % 2:  # half deleted by Qt, half by dropping the last reference
            view.deleteLater()
        del view
        qapp.sendPostedEvents(None, QEvent.DeferredDelete)
    gc.collect()
    err = capfd.readouterr().err
    assert all(r() is None for r in refs) and "Traceback" not in err and "attribute" not in err


def test_left_out_points_are_hollow_in_the_publication_figure():
    from astrowb.ui.plot import publish as P

    s = [SeriesSpec("data", [1, 2, 3], [1, 2, 3]), SeriesSpec("out", [4, 5], [4, 5], left_out=True)]
    fig = P.figure(FigureSpec([PanelSpec(AxisSpec("t"), AxisSpec("m"), s)]))
    data, out = fig.axes[0].lines[:2]
    assert out.get_markerfacecolor() == "none" and data.get_markerfacecolor() != "none"
