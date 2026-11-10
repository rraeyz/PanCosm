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
