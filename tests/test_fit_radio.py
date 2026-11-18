from PySide6.QtWidgets import QRadioButton, QVBoxLayout, QWidget


def test_a_wrapped_radio_button_still_turns_its_siblings_off(qtbot):
    from astrowb.ui.kit.fit import fit_width

    root = QWidget()
    qtbot.addWidget(root)
    lay = QVBoxLayout(root)
    short = QRadioButton("Linear", root)
    long = QRadioButton("A third body: light-travel time in a wide orbit around the pair " * 3, root)
    for b in (short, long):
        lay.addWidget(b)
    short.setChecked(True)
    fit_width(root, 200)
    assert long.text() == ""  # it was wrapped, moved into a holder
    long.click()
    assert long.isChecked() and not short.isChecked()
