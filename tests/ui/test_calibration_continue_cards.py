"""UI-16.2: the Continue stage's cards; synthetic result."""

import pytest

from astrowb.settings import Settings


@pytest.fixture
def page(qtbot, tmp_path):
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    win.open_area("calibrate")
    yield win, win.calibrate_page
    win.engine.shutdown()


def test_cards_are_disabled_until_a_result_exists(page):
    _, p = page
    assert set(p.continue_cards) == {"photometry", "stack", "images"}
    assert not any(c.isEnabled() for c in p.continue_cards.values())
    p.show_result({"calibrated": ["a.fits", "b.fits"], "masters": []})
    assert all(c.isEnabled() for c in p.continue_cards.values())


def test_a_card_click_does_the_hand_over_of_the_old_button(page):
    _, p = page
    got = {}
    for sig in (p.photometry_requested, p.images_requested, p.stack_button.clicked):
        sig.disconnect()  # the real hand-overs need real files
    p.photometry_requested.connect(lambda paths: got.setdefault("photometry", paths))
    p.images_requested.connect(lambda paths: got.setdefault("images", paths))
    stacked = []
    p.stack_button.clicked.connect(lambda: stacked.append(1))
    p.show_result({"calibrated": ["a.fits", "b.fits"], "masters": []})
    for key in ("photometry", "images", "stack"):
        p.continue_cards[key].click()
    assert got == {"photometry": ["a.fits", "b.fits"], "images": ["a.fits", "b.fits"]}
    assert stacked == [1]
