"""Arc lines identified once (IRAF databases, a reference arc of the spectrograph) used again on a new arc."""

import numpy as np
import pytest
from astropy.io import fits

from astrowb.spectroscopy import reidentify, wavecal

# lines of an HgAr lamp (Angstrom) and a reference arc on a linear grid, as LCO keeps for FLOYDS
LINES = [5460.75, 6965.43, 7067.22, 7147.04, 7272.94, 7383.98, 7635.11, 7948.18, 8115.31, 8264.52, 8521.44,
         8667.94, 9122.97, 9224.50, 9657.79]  # fmt: skip

IDENTIFY = """# Mon 18:46:11 27-Sep-2021
begin	identify ref_red - Ap 1
	id	ref_red
	task	identify
	image	ref_red - Ap 1
	aperture	1
	units	Angstroms
	features	{n}
{rows}	function legendre
	order 2
	coefficients	2
		2.
		2.
"""


def _lamp(pixels, fwhm=3.0, n=2048, rng=None):
    x = np.arange(n)
    y = np.zeros(n)
    for k, p in enumerate(pixels):
        y += (1000 + 400 * (k % 5)) * np.exp(-0.5 * ((x - p) / (fwhm / 2.3548)) ** 2)
    return y + (rng.normal(0, 3, n) if rng is not None else 0)


def _reference(tmp_path, step=2.956):
    flux = _lamp([(w - 4850) / step for w in LINES], n=1804)
    path = tmp_path / "ref_red.fits"
    fits.PrimaryHDU(flux.astype(np.float32), fits.Header({"CRVAL1": 4850.0, "CDELT1": step, "CRPIX1": 1.0})).writeto(
        path
    )
    rows = "".join(f"\t    {(w - 4850) / step + 1:10.2f} {w + 0.3:10.9g} {w:10.9g}   4.0 1 1 ArI\n" for w in LINES[:-1])
    rows += f"\t    {(LINES[-1] - 4850) / step + 1:10.2f} {LINES[-1]:10.9g}      INDEF   4.0 1 1 ArI\n"
    rows += "\t    1700.00 9800.0 9800.0   4.0 1 0 rejected\n"  # weight 0: rejected in IRAF
    (tmp_path / "database").mkdir()
    db = tmp_path / "database" / "idref_red"
    db.write_text(IDENTIFY.format(n=len(LINES) + 3, rows=rows))  # IRAF's count may exceed the lines written
    return path, db


def _night_arc(flip=False, rng=None):
    """The same lamp on the raw detector: another dispersion, a shift and a curved solution."""
    x = np.arange(2048)
    lam = 4770 + 3.48 * x + 2.0e-5 * (x - 1024) ** 2
    if flip:
        lam = lam[::-1]
    pix = [float(np.interp(w, lam, x) if not flip else np.interp(w, lam[::-1], x[::-1])) for w in LINES]
    return _lamp(pix, rng=rng), np.array(pix), lam


def test_read_identify_database(tmp_path):
    _, db = _reference(tmp_path)
    rec = reidentify.read_database(db)
    assert len(rec) == 1 and rec[0]["task"] == "identify" and rec[0]["aperture"] == 1
    waves = [f["wave"] for f in rec[0]["features"]]
    assert len(waves) == len(LINES) and 9800.0 not in waves  # the rejected line is left out
    assert waves[0] == LINES[0] and waves[-1] == pytest.approx(LINES[-1])  # user wavelength, or the fit if INDEF
    assert reidentify.find_reference(db) == tmp_path / "ref_red.fits"
    (tmp_path / "x.txt").write_text("nothing here\n")
    with pytest.raises(ValueError, match="no identified lines"):
        reidentify.read_database(tmp_path / "x.txt")


def test_read_ecidentify_database(tmp_path):
    db = tmp_path / "ecarc"
    db.write_text(
        "begin\tecidentify arc\n\tid\tarc\n\ttask\tecidentify\n\tunits\tAngstroms\n\tfeatures\t3\n"
        "\t\t  1   58   994.49  5882.6     5882.6242  4.0  1  1\n"
        "\t\t  2   57   857.72  5973.66    5973.6649  4.0  1  1\n"
        "\t\t  2   57   900.00  5977.00    INDEF      4.0  1  0\n"
        "\tfunction chebyshev\n"
    )
    feats = reidentify.read_database(db)[0]["features"]
    assert [(f["order"], f["wave"]) for f in feats] == [(58, 5882.6242), (57, 5973.6649)]


@pytest.mark.parametrize("flip", [False, True])
def test_lines_from_a_reference_arc(tmp_path, flip):
    ref, db = _reference(tmp_path)
    arc, true_pix, lam = _night_arc(flip, np.random.default_rng(4))
    peaks = wavecal.find_lines(arc)
    w, f = reidentify.reference_arc(ref)
    lines = [(x["wave"], x["label"]) for x in reidentify.read_database(db)[0]["features"]]
    r = reidentify.from_reference(arc, peaks, w, f, lines)
    assert r["matched"] == len(LINES) and r["correlation"] > 0.5 and r["rms"] < 0.5
    truth = dict(zip(LINES, true_pix, strict=True))
    assert all(abs(p - truth[min(LINES, key=lambda x: abs(x - wv))]) < 0.5 for p, wv, _ in r["pairs"])
    sol = wavecal.solve(peaks, np.array(LINES), [(p, wv) for p, wv, _ in r["pairs"]], 3)
    x = np.arange(2048)
    assert np.max(np.abs(sol(x[100:-100]) - lam[100:-100])) < 0.2  # Angstrom, over the illuminated part


def test_unrelated_reference_is_not_trusted(tmp_path):
    ref, db = _reference(tmp_path)
    rng = np.random.default_rng(1)
    arc = _lamp(rng.uniform(50, 2000, 15), rng=rng)  # another lamp altogether
    w, f = reidentify.reference_arc(ref)
    lines = [(x["wave"], x["label"]) for x in reidentify.read_database(db)[0]["features"]]
    r = reidentify.from_reference(arc, wavecal.find_lines(arc), w, f, lines)
    assert r["matched"] < len(LINES) // 2 or r["rms"] > 1


def test_shift_features_as_iraf_id_shift():
    feats = [{"pixel": p, "wave": 5000 + p} for p in (100.0, 400.0, 800.0, 1200.0, 1500.0)]
    peaks = [p + 12.3 for p in (100.0, 400.0, 800.0, 1200.0, 1500.0)] + [50.0, 950.0]  # two lines not in the list
    shift, found = reidentify.shift_features(peaks, feats)
    assert shift == pytest.approx(12.3, abs=0.2) and len(found) == 5
    assert all(abs(p - f["pixel"] - 12.3) < 1e-6 for p, f in found)


def test_reduce_tab_fills_the_table_and_undo(qtbot, tmp_path):
    from PySide6.QtWidgets import QApplication

    from astrowb.ui.spectro_page import ReduceTab

    ref, db = _reference(tmp_path)
    arc, _, _ = _night_arc(rng=np.random.default_rng(2))
    tab = ReduceTab()
    qtbot.addWidget(tab)
    assert tab.lines_from_reference(str(db)) is None and "Extract" in tab.status.text()
    tab.result = {"arc": arc.tolist(), "arc_peaks": wavecal.find_lines(arc).tolist()}
    rows = tab.lines_from_reference(str(ref))  # the reference arc chosen: its database is found next to it
    assert len(rows) == len(LINES) and tab.guesses.rowCount() == len(LINES)
    assert "Check them" in tab.status.text()
    tab.undo_stack.undo()
    assert tab.guesses.rowCount() == 0
    QApplication.processEvents()


def test_echelle_tab_lines_from_ecidentify(qtbot, tmp_path):
    from astrowb.ui.spectro_page import EchelleTab

    db = tmp_path / "ecarc"
    db.write_text(
        "begin\tecidentify arc\n\ttask\tecidentify\n\tfeatures\t4\n"
        "\t\t  1   58   994.49  5882.6     5882.6242  4.0  1  1\n"
        "\t\t  1   58  1063.52  5888.58    5888.5841  4.0  1  1\n"
        "\t\t  2   57   857.72  5973.66    5973.6649  4.0  1  1\n"
        "\t\t  2   57  1011.27  5987.30    5987.3016  4.0  1  1\n"
    )
    tab = EchelleTab()
    qtbot.addWidget(tab)
    tab.result = {"n_orders": 3, "arc_peaks": [[50.0], [1002.49, 1071.52, 300.0], [865.72, 1019.27]]}
    tab.first_order.setValue(59)
    tab.direction.setCurrentIndex(1)  # numbers decrease upwards: index 0 = 59, 1 = 58, 2 = 57
    rows = tab.lines_from_database(str(db))
    assert sorted(rows) == sorted(
        [["58", "1002.49", "5882.6242"], ["58", "1071.52", "5888.5841"], ["57", "865.72", "5973.6649"],
         ["57", "1019.27", "5987.3016"]]
    )  # fmt: skip
