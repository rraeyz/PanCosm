"""OC-W accept: star name -> minima (a file, until OC-4 fetches them) -> ephemeris fitted -> LTTE fitted -> results
exported in six clicks (Load file, Look up, Fit on the linear ephemeris, the third-body model, Fit, Export). The
look-up is answered in the test, never by VSX; the minima are synthetic: an ephemeris plus a light-time orbit of a
known amplitude, primaries (CCD) and secondaries (visual), each with its error."""

import csv

import numpy as np
import pytest

T0, P, AMP, P3 = 2455000.1234, 0.8123456, 0.0050, 2900.0  # days; the injected third body
CLICKS = ("click ", "choose ", "menu ")


def _minima(folder):
    rng = np.random.default_rng(11)
    e = np.sort(rng.choice(np.arange(0, int(12 * 365.25 / P)), 120, replace=False))
    lines = ["# time  error  kind  method  (synthetic)"]
    for k, n in enumerate(e):
        secondary = k % 4 == 3
        t = T0 + P * (n + 0.5 * secondary)
        t += AMP * np.sin(2 * np.pi * (t - T0) / P3) + rng.normal(0, 0.0004, ())
        lines.append(f"{t:.5f} 0.0004 {'II' if secondary else 'I'} {'vis' if secondary else 'CCD'}")
    path = folder / "minima.txt"
    path.write_text("\n".join(lines) + "\n")
    return path


def _flow(walk, tmp_path):
    h = walk("en")
    h.area("oc")
    page = h.page
    page.ephemeris_requested.disconnect()  # no VSX: the look-up is answered here
    page.ephemeris_requested.connect(lambda name: page.set_ephemeris({"name": name, "t0": T0, "period": P}))
    out = tmp_path / "results.csv"
    h.answer(_minima(tmp_path))
    h.click("load_button")  # 1
    page.star.setText("NY Vir")  # typed, not clicked
    h.click("look_up")  # 2
    h.click("fit_button")  # 3: the linear ephemeris first
    h.wait(lambda: page.fit_result is not None)
    h.click("ltte")  # 4
    h.click("fit_button")  # 5
    h.wait(lambda: hasattr(page.fit_result, "p3"))
    h.answer(out)
    h.click("results_button")  # 6
    h.check()
    return h, page, out, sum(t[0].startswith(CLICKS) for t in h.timings)


def test_star_to_exported_ltte_table_in_six_clicks(walk, tmp_path):
    h, page, out, clicks = _flow(walk, tmp_path)
    assert clicks == 6, h.timings  # today's count; the goal is six
    f = page.fit_result
    assert abs(f.amplitude - AMP) < 3 * f.errors["amplitude"]
    row = next(r for r in csv.reader(out.read_text().splitlines()) if r and r[0].startswith("A (semi"))
    assert abs(float(row[1]) - AMP * 1440) < 3 * float(row[2])  # the exported amplitude, minutes


def test_symbols_differ_for_primary_and_secondary_and_by_method(walk, tmp_path):
    _, page, _, _ = _flow(walk, tmp_path)
    pts = {s.name: s.symbol for s in page.plot.figure.panels[0].series if s.kind == "points"}
    assert set(pts) == {"primary · CCD", "secondary · vis"} and pts["primary · CCD"] != pts["secondary · vis"]


@pytest.mark.xfail(
    strict=True,
    reason="OC-W: a click on an O−C point does not select its table row yet (UI-16.5 does "
    "not describe it; the O−C series are not pickable)",
)
def test_a_click_on_a_point_selects_its_row(walk, tmp_path):
    _, page, _, _ = _flow(walk, tmp_path)
    series = page.plot.figure.panels[0].series[0]
    assert series.pickable
    page.plot.point_clicked.emit(series.name, 0)
    assert page.minima_input.selectionModel().hasSelection()
