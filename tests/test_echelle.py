"""Echelle reduction on a synthetic cross-dispersed frame with known truth (orders, blaze, ThAr arc)."""

import numpy as np
import pytest

from astrowb.spectroscopy import echelle, wavecal

NX, NY = 2048, 400
ORDERS = np.arange(30, 46)  # absolute order numbers, bottom to top
SIGMA_Y = 1.6
ABS_LINES = [3820.4, 3933.7, 3968.5, 4045.8, 4101.7, 4226.7, 4340.5, 4383.5, 4861.3, 5167.3, 5183.6, 5269.5, 5328.0]


def grating(x):
    """m * lambda (Angstrom) along x: the same for every order (grating equation)."""
    return 170000.0 + 4.25 * (x - 1024) - 2e-4 * (x - 1024) ** 2


def wave_true(x, m):
    return grating(x) / m


def order_y(x, m):
    return 25.0 + 22.0 * (m - ORDERS[0]) + 0.01 * (x - 1024) + 4e-6 * (x - 1024) ** 2


def blaze_true(x, m):
    return np.sinc((x - 1024 - 30 * (m - 37)) / 1500.0) ** 2


def star(wave):
    f = np.ones_like(wave)
    for line in ABS_LINES:
        f -= 0.5 * np.exp(-0.5 * ((wave - line) / 0.3) ** 2)
    return f


def _frame(fn, rng, noise=True):
    x = np.arange(NX)
    y = np.arange(NY)[:, None]
    img = np.zeros((NY, NX))
    for m in ORDERS:
        prof = np.exp(-0.5 * ((y - order_y(x, m)[None, :]) / SIGMA_Y) ** 2) / (np.sqrt(2 * np.pi) * SIGMA_Y)
        img += prof * fn(x, m)[None, :]
    img += 50.0  # bias-subtracted background / scattered light
    if noise:
        img = rng.poisson(np.clip(img, 0, None)).astype(float) + rng.normal(0, 3, img.shape)
    return img


@pytest.fixture(scope="module")
def frames():
    rng = np.random.default_rng(5)
    thar = wavecal.load_line_list("thar")
    strengths = dict(zip(thar, rng.uniform(300, 8000, len(thar)), strict=True))

    def arc(x, m):
        w = wave_true(x, m)
        out = np.zeros(NX)
        for lam in thar[(thar > w.min() - 1) & (thar < w.max() + 1)]:
            px = np.interp(lam, w, x)
            out += strengths[lam] * np.exp(-0.5 * ((x - px) / 1.3) ** 2)
        return out

    return {
        "flat": _frame(lambda x, m: 40000.0 * blaze_true(x, m), rng),
        "arc": _frame(arc, rng),
        "star": _frame(lambda x, m: 8000.0 * blaze_true(x, m) * star(wave_true(x, m)), rng),
        "thar": thar,
    }


@pytest.fixture(scope="module")
def traces(frames):
    return echelle.trace_orders(frames["flat"])


def test_orders_found_and_traced(frames, traces):
    rows = echelle.find_orders(frames["flat"])
    assert len(rows) == len(ORDERS)
    assert np.max(np.abs(rows - order_y(NX // 2, ORDERS))) < 0.2
    x = np.arange(0, NX, 16)
    for coef, m in zip(traces, ORDERS, strict=True):
        assert np.max(np.abs(np.polyval(coef, x) - order_y(x, m))) < 0.15


def test_wavelength_solution_and_order_numbers(frames, traces):
    arc, _ = echelle.extract(frames["arc"], traces, method="boxcar", subtract_sky=False)
    peaks = [wavecal.find_lines(a) for a in arc]
    # identify three lines spread along each of two orders, as a user would in the arc viewer
    guesses = []
    for k in (5, 10):
        m = ORDERS[k]
        for px_hint in (300, 1024, 1750):
            px = peaks[k][np.argmin(np.abs(peaks[k] - px_hint))]
            lam = wave_true(px, m)
            lam = frames["thar"][np.argmin(np.abs(frames["thar"] - lam))]  # the catalogue value
            guesses.append((m, px, lam))
    sol = echelle.solve_2d(peaks, ORDERS, frames["thar"], guesses, nx=NX)
    x = np.arange(NX)
    worst = max(np.max(np.abs(sol(x, m) - wave_true(x, m))) for m in ORDERS)
    assert worst < 0.005  # Angstrom, ~0.04 pixel (measured 0.0023)
    assert sol.rms < 0.01 and sol.n_lines > 300
    assert sol.wavelengths(NX).shape == (len(ORDERS), NX)
    # absolute order from two adjacent orders at the same pixel (no prior numbering needed)
    m = echelle.order_number(wave_true(1024, 38), wave_true(1024, 37))
    assert round(m) == 38 and abs(m - 38) < 1e-6


def test_wavelength_solution_refuses_too_few_lines(frames, traces):
    with pytest.raises(ValueError):
        echelle.solve_2d([np.array([100.0])] * 2, ORDERS[:2], frames["thar"], [(30, 1, 5000.0)] * 4)


def test_blaze_and_merge_recover_the_spectrum(frames, traces):
    flat, _ = echelle.extract(frames["flat"], traces, method="boxcar")
    bl = echelle.blaze(flat)
    x = np.arange(NX)
    for k, m in enumerate(ORDERS):  # the blaze shape, where it matters
        b = blaze_true(x, m) / blaze_true(x, m).max()
        use = b > 0.2
        assert np.max(np.abs(bl[k][use] - b[use])) < 0.03
    flux, err = echelle.extract(frames["star"], traces, method="optimal")
    waves = np.array([wave_true(x, m) for m in ORDERS])
    w, f, e = echelle.merge(waves, flux, err, bl, min_blaze=0.2)
    assert np.all(np.diff(w) > 0) and w[0] < 3800 and w[-1] > 5600
    ratio = f / star(w)
    scale = np.median(ratio)
    assert scale == pytest.approx(8000, rel=0.03)
    resid = ratio / scale - 1
    assert np.percentile(np.abs(resid), 95) < 0.03
    # the reported errors describe the scatter
    pull = (f - scale * star(w)) / e
    assert 0.6 < np.std(pull[np.abs(resid) < 0.2]) < 1.6


class _Ctx:
    def progress(self, *a):
        pass

    def check(self):
        pass


@pytest.mark.parametrize("coude", [False, True])
def test_echelle_step_writes_a_merged_spectrum(frames, tmp_path, coude):
    from astropy.io import fits

    from astrowb.engine.steps import execute
    from astrowb.spectroscopy import spectrum_io

    paths = {}
    for name in ("star", "flat", "arc"):
        paths[name] = tmp_path / f"{name}.fits"
        img = frames[name][:, ::-1].T if coude else frames[name]  # dispersion along columns, reversed
        fits.PrimaryHDU(img.astype(np.float32)).writeto(paths[name])
    arc, _ = echelle.extract(frames["arc"], echelle.trace_orders(frames["flat"]), method="boxcar", subtract_sky=False)
    guesses = []
    for k in (3, 12):
        peaks = wavecal.find_lines(arc[k])
        for hint in (300, 1024, 1750):
            px = peaks[np.argmin(np.abs(peaks - hint))]
            lam = frames["thar"][np.argmin(np.abs(frames["thar"] - wave_true(px, ORDERS[k])))]
            guesses.append([int(ORDERS[k]), float(px), float(lam)])
    out = execute(
        "spectroscopy.echelle",
        {
            "science": str(paths["star"]),
            "flat": str(paths["flat"]),
            "arc": str(paths["arc"]),
            "guesses": guesses,
            "output": str(tmp_path / "merged.fits"),
        },
        {"first_order": int(ORDERS[0]), "min_blaze": 0.2} | ({"orientation": "y", "reverse": True} if coude else {}),
        _Ctx(),
    )["echelle"]
    assert out["n_orders"] == len(ORDERS) and out["solution"]["rms"] < 0.01
    w, f, _, _ = spectrum_io.read(out["path"])
    ratio = f / star(w)
    assert np.percentile(np.abs(ratio / np.median(ratio) - 1), 95) < 0.03


def test_scattered_light_is_measured_between_the_orders(frames, traces):
    yy, xx = np.mgrid[:NY, :NX]
    glow = 80.0 + 60.0 * np.exp(-(((yy - 200) / 150.0) ** 2) - ((xx - 900) / 900.0) ** 2)  # a broad halo
    model = echelle.scattered_light(frames["flat"] + glow, traces)
    inside = slice(40, NY - 40), slice(100, NX - 100)
    resid = (model - glow - 50.0)[inside]  # the frames carry a flat 50 counts of background too
    assert np.median(np.abs(resid)) < 3.0 and np.percentile(np.abs(resid), 95) < 10.0


def test_lines_left_out_by_hand_are_not_fitted(frames, traces):
    arc, _ = echelle.extract(frames["arc"], traces, method="boxcar", subtract_sky=False)
    peaks = [wavecal.find_lines(a) for a in arc]
    guesses = []
    for k in (5, 10):
        for hint in (300, 1024, 1750):
            px = peaks[k][np.argmin(np.abs(peaks[k] - hint))]
            guesses.append(
                (ORDERS[k], px, frames["thar"][np.argmin(np.abs(frames["thar"] - wave_true(px, ORDERS[k])))])
            )
    sol = echelle.solve_2d(peaks, ORDERS, frames["thar"], guesses, nx=NX)
    assert len(sol.lines) >= sol.n_lines and all(len(row) == 5 for row in sol.lines)
    used = [row for row in sol.lines if row[4]]
    assert np.sqrt(np.mean([row[3] ** 2 for row in used])) == pytest.approx(sol.rms, rel=1e-6)
    m, x = used[0][0], used[0][1]
    again = echelle.solve_2d(peaks, ORDERS, frames["thar"], guesses, nx=NX, exclude=[(m, x)])
    assert not any(row[0] == m and abs(row[1] - x) < 1.5 for row in again.lines)
    assert again.rms < 0.01


def test_echelle_step_saves_every_order(frames, tmp_path):
    from astropy.io import fits

    from astrowb.engine.steps import execute

    paths = {}
    for name in ("star", "flat", "arc"):
        paths[name] = tmp_path / f"{name}.fits"
        fits.PrimaryHDU(frames[name].astype(np.float32)).writeto(paths[name])
    arc, _ = echelle.extract(frames["arc"], echelle.trace_orders(frames["flat"]), method="boxcar", subtract_sky=False)
    guesses = []
    for k in (3, 12):
        peaks = wavecal.find_lines(arc[k])
        for hint in (300, 1024, 1750):
            px = peaks[np.argmin(np.abs(peaks - hint))]
            lam = frames["thar"][np.argmin(np.abs(frames["thar"] - wave_true(px, ORDERS[k])))]
            guesses.append([int(ORDERS[k]), float(px), float(lam)])
    out = execute(
        "spectroscopy.echelle",
        {k: str(v) for k, v in paths.items() if k != "star"}
        | {"science": str(paths["star"]), "guesses": guesses, "output": str(tmp_path / "m.fits")},
        {"first_order": int(ORDERS[0]), "min_blaze": 0.2, "scatter": True},
        _Ctx(),
    )["echelle"]
    with fits.open(out["orders_path"]) as h:
        assert h[0].data.shape == (len(ORDERS), NX) and h["WAVE"].data.shape == (len(ORDERS), NX)
        assert h[0].header["ORDERS"].split(",")[0] == str(ORDERS[0]) and h[0].header["SCATSUB"]
        assert np.allclose(h["WAVE"].data[4], wave_true(np.arange(NX), ORDERS[4]), atol=0.01)
    assert out["solution"]["lines"] and out["solution"]["rms"] < 0.01


def test_echelle_tab_leaves_out_clicked_lines(qtbot, tmp_path):
    from types import SimpleNamespace

    from astrowb.ui.spectro_page import EchelleTab

    tab = EchelleTab()
    qtbot.addWidget(tab)
    tab.resize(1200, 800)
    tab.show()
    lines = [[30.0, 100.0 + 50 * i, 5000.0 + i, 0.001 * (i % 5 - 2), True] for i in range(30)] + [
        [31.0, 900.0, 4990.0, 0.05, False]
    ]
    r = {
        "n_orders": 2,
        "flux": [[1.0] * 50] * 2,
        "arc": [[0.0] * 50] * 2,
        "arc_peaks": [[10.0], [20.0]],
        "merged": None,
        "solution": {"rms": 0.0014, "n_lines": 30, "lines": lines},
    }
    tab.show_result(r)
    tab.plot.canvas.draw()
    ax = tab._resid_ax
    px, py = ax.transData.transform((lines[7][1], lines[7][3] * 1000))
    tab._plot_clicked(SimpleNamespace(inaxes=ax, x=px, y=py, xdata=None))
    assert tab.excluded_lines == [[30.0, lines[7][1]]] and "1 arc line" in tab.status.text()
    from PySide6.QtWidgets import QTableWidgetItem

    tab.scatter.setChecked(True)
    tab.science.edit.setText(str(tmp_path / "science.fits"))
    tab.arc.edit.setText(str(tmp_path / "arc.fits"))
    tab.first_order.setValue(30)
    for i, (m, x, lam) in enumerate([(30, 1, 5000), (30, 2, 5001), (31, 1, 4900), (31, 2, 4901)]):
        tab.guesses.insertRow(i)
        for c, v in enumerate((m, x, lam)):
            tab.guesses.setItem(i, c, QTableWidgetItem(str(v)))
    with qtbot.waitSignal(tab.reduce_requested) as sig:
        tab.refit_button.click()
    params = sig.args[1]
    assert params["exclude"] == [[30.0, lines[7][1]]] and params["scatter"]
    tab.forget_excluded()
    assert tab.excluded_lines == []


def test_orders_checked_by_hand(frames, tmp_path, qtbot):
    """PLAN 4.8 item 13: the orders are shown on the flat; a missed order is added by clicking anywhere on it,
    a wrong one is removed by clicking its trace, and the reduction uses the checked list."""
    from types import SimpleNamespace

    from astropy.io import fits

    from astrowb.engine.steps import execute
    from astrowb.ui.spectro_page import EchelleTab

    class Ctx:
        def progress(self, *a):
            pass

        def check(self):
            pass

    flat = tmp_path / "flat.fits"
    fits.PrimaryHDU(frames["flat"].astype(np.float32)).writeto(flat)
    auto = execute("spectroscopy.orders", {"image": str(flat)}, {}, Ctx())["orders"]
    assert len(auto["rows"]) == len(ORDERS) and auto["failed"] == [] and auto["nx"] == NX
    # the automatic search missed order 5: the user clicks on it far from the centre column
    missed = [r for i, r in enumerate(auto["rows"]) if i != 5]
    coefs = [c for i, c in enumerate(auto["traces"]) if i != 5]
    x_click = 200.0
    row = echelle.row_at_centre(coefs, x_click, order_y(x_click, ORDERS[5]) + 0.8, NX)
    assert abs(row - order_y(NX // 2, ORDERS[5])) < 1.0  # moved along the curvature to the centre column
    fixed = execute("spectroscopy.orders", {"image": str(flat)}, {"rows": sorted(missed + [row])}, Ctx())["orders"]
    x = np.arange(0, NX, 16)
    assert np.max(np.abs(np.polyval(fixed["traces"][5], x) - order_y(x, ORDERS[5]))) < 0.15
    # the tab: draw, remove one order by clicking its trace, add it back by clicking on it
    tab = EchelleTab()
    qtbot.addWidget(tab)
    tab.resize(1200, 800)
    tab.show()
    tab.flat.edit.setText(str(flat))
    tab.science.edit.setText(str(flat))
    tab.show_orders(auto)
    tab.plot.canvas.draw()
    ax = tab._flat_ax
    tab._plot_clicked(SimpleNamespace(inaxes=ax, xdata=700.0, ydata=float(order_y(700.0, ORDERS[3]))))
    assert len(tab.order_rows) == len(ORDERS) - 1 and "15 orders" in tab.status.text()
    with qtbot.waitSignal(tab.orders_requested) as sig:
        tab._plot_clicked(
            SimpleNamespace(inaxes=tab._flat_ax, xdata=700.0, ydata=float(order_y(700.0, ORDERS[3]) + 0.5))
        )
    assert len(sig.args[1]["rows"]) == len(ORDERS)  # traced again with the order put back
    tab.show_orders(execute("spectroscopy.orders", sig.args[0], sig.args[1], Ctx())["orders"])
    with qtbot.waitSignal(tab.reduce_requested) as sig:
        tab.extract_button.click()
    assert np.allclose(sig.args[1]["rows"], order_y(NX // 2, ORDERS), atol=0.2)  # click refined to the order
    out = execute("spectroscopy.echelle", {"science": str(flat), "flat": str(flat)}, sig.args[1], Ctx())["echelle"]
    assert out["n_orders"] == len(ORDERS)
