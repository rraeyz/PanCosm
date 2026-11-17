"""UI-19 / UI-8: the quick tour and the area tour in four languages at 1366 x 768 (no stop off screen), the tour's
last offer, and every guided task's Show me followed in each language."""

import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QRect

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import Harness  # noqa: E402

LANGS = ["en", "tr", "de", "es"]


def _inside(tour, rect):
    return tour.rect().contains(rect.adjusted(0, 0, -1, -1)) and tour.rect().contains(tour.bubble.geometry())


@pytest.fixture
def harness(qtbot, tmp_path):
    made = []

    def start(lang):
        made.append(Harness(qtbot, tmp_path, lang))
        made[-1].main.resize(1366, 768)
        made[-1].main.show()
        qtbot.waitExposed(made[-1].main)
        return made[-1]

    yield start
    for h in made:
        h.close()


@pytest.mark.parametrize("lang", LANGS)
def test_quick_tour_has_six_stops_on_screen_and_offers_the_practice_night(harness, lang):
    main = harness(lang).main
    tour = main.start_tour()
    assert len(tour.steps) == 6
    for i in range(6):
        rect = tour._rect()
        assert rect is not None and _inside(tour, rect.intersected(tour.rect())) and tour.text.text(), i
        assert tour.offer_button.isVisible() == (i == 5)
        if i < 5:
            tour.advance()
    started = []
    main.practice_data = lambda then=None: started.append(then)  # the folder dialog and the step are not the test
    tour.offer_button.click()
    assert tour.finished and len(started) == 1 and callable(started[0])


@pytest.mark.parametrize("lang", LANGS)
def test_area_tour_stops_are_inside_the_window(harness, lang):
    h = harness(lang)
    win = h.main.open_area("photometry")
    win.resize(1366, 768)
    win.show()
    h.qtbot.waitExposed(win)
    from astrowb.ui import tour as tours

    t = tours.start_area(win)
    for _ in t.steps:
        rect = t._rect()
        assert rect is not None and t.rect().contains(rect.intersected(t.rect()).center()) and t.text.text()
        assert _inside(t, QRect(rect.intersected(t.rect()))), rect
        t.advance()
    assert t.finished


@pytest.mark.parametrize("lang", LANGS)
def test_every_guided_step_is_followed_by_show_me(harness, lang):
    from astrowb.ui import help_checks
    from astrowb.ui.kit import guided

    h = harness(lang)
    for task in guided.available(lang):
        bar = help_checks.start_guided(h.main, task)
        for i, (_, text, _) in enumerate(task["steps"]):
            assert text and bar.show_me() and bar.mark.isVisible(), (task["title"], i)
            target = bar.target()[0]
            assert bar.mark.geometry().contains(bar.widget().mapTo(target, bar.widget().rect().center())), i
            bar.next()


def test_area_tour_of_a_window_not_on_screen_does_nothing(harness):
    """Menu Window → another area's window and its Tour, before it was ever shown: no stop to point at, no error."""
    from astrowb.ui import tour as tours

    win = harness("en").main.open_area("plan")
    win.hide()
    assert tours.start_area(win) is None
