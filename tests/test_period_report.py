"""PER-16: the peaks table, the methods paragraph, the VSX sheet."""

from astrowb.timeseries import report


def test_report_texts():
    table = report.peaks_latex([(0.3651234, 0.0000021, 0.812, 1.2e-30, "best"), (0.18256, 0.00001, 0.3, None, "P/2")])
    assert "$0.3651234(21)$ & 0.812 & 1.2e-30 & best" in table and "& -- &" in table
    text = report.methods_text("GLS", 1500, 87.25, "0.05–40 d in steps of 1/(5T)", "Baluev's approximation",
                               ["TESS", "ZTF"])  # fmt: skip
    assert "1500 points spanning 87.2 days" in text or "87.3 days" in text
    sheet = report.vsx_sheet("ASASSN-V J000000", "EW", 0.3651234, 0.0000021, 2459000.12345, 0.00012, 12.1, 12.6,
                             "V", 25, eclipsing=True)  # fmt: skip
    assert "Period: 0.3651234(21) d" in sheet and "Epoch: 2459000.12345(12) (minimum)" in sheet
    assert sheet.endswith("Eclipse duration: 25 %")
