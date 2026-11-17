from astrowb.timeseries.combinations import combination_notes
from astrowb.ui.frequency_page import FrequencyPage


def test_harmonic_combination_and_alias_notes():
    freqs = [1.0, 2.0, 3.5, 4.5, 2.0027, 7.3]
    notes = combination_notes(freqs, 30.0)  # resolution 0.05 c/d
    assert notes[0] == []
    assert {"kind": "harmonic", "n": 2, "i": 1} in notes[1]
    assert {"kind": "combination", "i": 3, "j": 1, "sign": 1} in notes[3]  # 4.5 = 3.5 + 1.0
    assert {"kind": "alias", "i": 1, "k": 1} in notes[4]
    assert notes[2] == [] and notes[5] == []


def test_the_table_shows_the_notes_in_words(qtbot):
    class Page:
        time, flux = [], []

    page = FrequencyPage(Page())
    qtbot.addWidget(page)
    row = {"freq": 1.0, "freq_err": 0.01, "amp": 1.0, "amp_err": 0.1, "phase": 0.1, "phase_err": 0.01, "snr": 9.0}
    note = [{"kind": "harmonic", "n": 2, "i": 1}, {"kind": "combination", "i": 2, "j": 1, "sign": -1}]
    out = {"frequencies": [row, row | {"freq": 2.0, "note": note}], "maxima": [], "rms": 0.1, "grid": [1.0, 2.0],
           "spectrum": [0, 1], "residual_spectrum": [0, 1], "window": [1, 0]}  # fmt: skip
    page.show_result(out)
    col = page.table.model.table["Note"]
    assert col[0] == "" and "2·f1" in col[1] and "f2 − f1" in col[1] and col[1].startswith("possible")
