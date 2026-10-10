"""Results tables for papers: rounding to the error, CSV and LaTeX."""

import numpy as np

from astrowb.ui.plot.export import rounded, save_results


def test_rounded_to_the_error():
    assert rounded(1.234567, 0.000123) == ("1.23457", "0.00012")
    assert rounded(12.3, None) == ("12.3", "")
    assert rounded(2459500.2512342, 0.0000312) == ("2459500.251234", "0.000031")
    assert rounded(86.46, 0.97) == ("86.46", "0.97")
    assert rounded(1234.0, 56.0) == ("1234", "56")
    assert rounded(5.0, float("nan")) == ("5", "")
    assert rounded(2460512.123456, None) == ("2460512.123456", "")  # a BJD without an error keeps its digits


def test_save_results_csv_and_latex(tmp_path):
    rows = [("P", 2.1500082, 3.1e-6, "d"), ("e_3", 0.31, None, ""), ("M1", 1.234, 0.0456, "Msun")]
    save_results(tmp_path / "r.csv", rows, "A caption")
    lines = (tmp_path / "r.csv").read_text(encoding="utf-8").splitlines()
    assert lines[0] == "# A caption" and lines[1] == "parameter,value,error,unit"
    assert lines[2] == "P,2.1500082,0.0000031,d" and lines[3] == "e_3,0.31,,"
    save_results(tmp_path / "r.tex", rows, "Fit of 10% of the data")
    tex = (tmp_path / "r.tex").read_text(encoding="utf-8")
    assert r"\caption{Fit of 10\% of the data}" in tex and r"$2.1500082 \pm 0.0000031$ & d" in tex
    assert r"e\_3 & $0.31$" in tex and tex.count(r"\\") == 4  # header + three rows


def test_oc_and_models_tables(qtbot, tmp_path):
    from astrowb.ui.workspaces import OCPage

    page = OCPage()
    qtbot.addWidget(page)
    assert page.fit_table() is None and "first" in page.result.text()
    t0, p = 2455867.402743, 2.1500082
    rng = np.random.default_rng(4)
    page.text.setPlainText(
        "\n".join(f"{t0 + e * p + rng.normal(0, 0.0003):.6f} 0.0003 I" for e in (-500, -120, 0, 300, 700, 1050))
    )
    page.t0.setText(str(t0))
    page.period.setText(str(p))
    page.run_fit()
    rows, caption = page.fit_table()
    assert [r[0] for r in rows] == ["T0", "P", "chi2_r"] and "6 times of minimum" in caption
    assert abs(rows[1][1] - p) < 3 * rows[1][2]
