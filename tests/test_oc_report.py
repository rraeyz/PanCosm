"""OC-12: the journal tables (stored expected text), predictions, the methods paragraph."""

import numpy as np
import pytest

from astrowb.timeseries import oc_report as rep

MODELS = {"Linear": {"$T_0$": (2459000.123456, 0.00012), "$P$ (d)": (0.365123451, 0.000000031)},
          "LTTE": {"$T_0$": (2459000.12341, 0.0002), "$P$ (d)": (0.36512341, 0.00000005),
                   "$e_3$": (0.41, 0.032)}}  # fmt: skip

AA = r"""\begin{table}
\caption{Fitted O$-$C models}
\label{tab:oc}
\centering
\begin{tabular}{lcc}
\hline\hline
Parameter & Linear & LTTE \\
\hline
$T_0$ & $2459000.12346(12)$ & $2459000.12341(20)$ \\
$P$ (d) & $0.365123451(31)$ & $0.365123410(50)$ \\
$e_3$ & -- & $0.410(32)$ \\
\hline
\end{tabular}
\end{table}"""


def test_the_aa_table_is_the_stored_text():
    assert rep.parameter_table(MODELS) == AA


def test_the_aastex_table_and_the_plus_minus_form():
    text = rep.parameter_table(MODELS, "aastex", "pm")
    assert text.startswith(r"\begin{deluxetable}{lcc}") and r"\colhead{LTTE}" in text
    assert r"$0.365123451 \pm 0.000000031$" in text and text.endswith(r"\end{deluxetable}")
    with pytest.raises(ValueError):
        rep.parameter_table(MODELS, "mnras")
    assert rep.paren(1.5, 0) == "1.5"


def test_next_minima_and_methods():
    got = rep.next_minima(2459000.0, 0.4, 2459010.05, 2459011.0)
    assert [k for _e, _t, k in got] == ["II", "I", "II", "I", "II"] and got[0][0] == 25.5
    assert all(2459010.05 <= t <= 2459011.0 for _e, t, _k in got)
    primaries = rep.next_minima(2459000.0, 0.4, 2459010.05, 2459011.0, secondary=False)
    assert [e for e, _t, _k in primaries] == [26.0, 27.0]
    shifted = rep.next_minima(2459000.0, 0.4, 2459010.0, 2459011.0, model=lambda e: 2459000.01 + 0.4 * np.asarray(e))
    assert shifted[0][1] == pytest.approx(2459010.01)
    models = ["a linear ephemeris", "LTTE"]
    text = rep.methods_text(87, "BJD_TDB", "Kwee–van Woerden", "the inverse squared errors", models,
                            "differential-evolution MCMC", ["the O−C gateway"])  # fmt: skip
    assert text.startswith("We used 87 times of minimum in BJD_TDB") and "O−C gateway" in text
