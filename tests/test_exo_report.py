"""EXO-12: the paper table in both styles and Markdown."""

import pytest

from astrowb.exoplanets import report

ROWS = [("Stellar", "$M_*$", "Mass ($M_\\odot$)", (0.928, 0.044, 0.046)),
        ("Planetary", "$P$", "Period (days)", (2.8997360, 0.0000020, 0.0000021)),
        ("Planetary", "$R_P/R_*$", "Radius ratio", (0.1109, 0.0016, 0.0019))]  # fmt: skip


def test_the_tables():
    aa = report.latex(ROWS)
    assert "\\multicolumn{3}{l}{\\textit{Stellar}} \\\\" in aa and aa.count("\\textit{") == 2
    assert "$P$ & Period (days) & $2.8997360^{+0.0000021}_{-0.0000020}$ \\\\" in aa
    assert "$0.928^{+0.046}_{-0.044}$" in aa
    assert report.latex(ROWS, "aastex").startswith("\\begin{deluxetable}{llc}")
    md = report.markdown(ROWS)
    assert "| $R_P/R_*$ | Radius ratio | 0.1109 +0.0019 −0.0016 |" in md
    with pytest.raises(ValueError):
        report.latex(ROWS, "mnras")
