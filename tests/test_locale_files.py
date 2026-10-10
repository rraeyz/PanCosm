"""ARC-18 item 4: files written under a German (decimal-comma) locale still use decimal points."""

import locale
import re

import numpy as np
from astropy.table import Table


def test_no_decimal_comma_in_written_files(qapp, tmp_path):
    from PySide6.QtCore import QLocale

    from astrowb.core import table as T
    from astrowb.ui.plot.export import save_results

    before = QLocale()
    QLocale.setDefault(QLocale(QLocale.German, QLocale.Germany))
    try:
        try:
            locale.setlocale(locale.LC_NUMERIC, "de_DE.UTF-8")
        except locale.Error:
            pass  # not installed on this machine: Qt's default still is German
        t = Table({"bjd": [2460512.123456], "mag": [12.345], "mag_err": [0.012]})
        texts = [T.write(t, tmp_path / f"t.{ext}").read_text(encoding="utf-8") for ext in ("csv", "ecsv", "tex", "md")]
        save_results(tmp_path / "r.csv", [("P", 2.1500082, 1e-6, "d")])
        texts.append((tmp_path / "r.csv").read_text(encoding="utf-8"))
        for text in texts:
            assert not re.search(r"2460512,1|12,34|2,150008", text), text  # the numbers, not CSV's separators
            assert "2460512.12" in text or "2.150008" in text
    finally:
        locale.setlocale(locale.LC_NUMERIC, "C")
        QLocale.setDefault(before)
        np.set_printoptions()
