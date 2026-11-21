"""UI-16.12: drag a step from the library onto the chain, drag a card to reorder."""

from PySide6.QtCore import QPoint

from astrowb.settings import Settings
from astrowb.ui.automation_page import AutomationPage
from astrowb.ui.step_chain import CARD_MIME
from astrowb.ui.step_library import STEP_MIME, StepLibrary


def _page(qtbot, tmp_path):
    page = AutomationPage(Settings(tmp_path))
    qtbot.addWidget(page)
    page.set_automation({"name": "t", "steps": [{"step": "calibration.scan"}, {"step": "calibration.run"}]})
    return page


def _ids(page):
    return [e["step"] for e in page.auto["steps"]]


def _drop(chain, fmt, payload, at):
    """The signal dropEvent gives for the mime data (the place is computed by drop_place, tested below)."""
    (chain.stepDropped.emit(payload, at) if fmt == STEP_MIME else chain.cardMoved.emit(int(payload), at))


def test_library_lists_steps_and_gives_the_id(qtbot, tmp_path):
    page = _page(qtbot, tmp_path)
    lib = page.findChild(StepLibrary)
    assert lib.count() > 5
    mime = lib.mimeData([lib.item(0)])
    assert bytes(mime.data(STEP_MIME)).decode() == lib.item(0).data(256)


def test_drop_from_the_library_inserts_at_the_place(qtbot, tmp_path):
    page = _page(qtbot, tmp_path)
    _drop(page.steps, STEP_MIME, "fits.save_as", 1)
    assert _ids(page) == ["calibration.scan", "fits.save_as", "calibration.run"]
    assert page.steps.count() == 3 and page.steps.currentRow() == 1
    # the badge of the last card follows the new order: its frames still come from the scan
    assert "frames" not in page.steps._group.button(2).badge.text()


def test_drop_of_a_card_reorders_and_badges_follow(qtbot, tmp_path):
    page = _page(qtbot, tmp_path)
    _drop(page.steps, CARD_MIME, "0", 2)  # the first card to the end
    assert _ids(page) == ["calibration.run", "calibration.scan"]
    assert "frames" in page.steps._group.button(0).badge.text()  # nothing gives frames before it now
    _drop(page.steps, CARD_MIME, "1", 0)
    assert _ids(page) == ["calibration.scan", "calibration.run"]
    _drop(page.steps, CARD_MIME, "0", 1)  # onto its own place: nothing changes
    assert _ids(page) == ["calibration.scan", "calibration.run"]


def test_drop_place_counts_cards_above(qtbot, tmp_path):
    page = _page(qtbot, tmp_path)
    page.resize(700, 700)
    page.show()
    chain = page.steps
    first = chain._group.button(0)
    y = chain.widget().mapTo(chain.viewport(), first.mapTo(chain.widget(), first.rect().center())).y()
    assert chain.drop_place(QPoint(5, y - 3)) == 0
    assert chain.drop_place(QPoint(5, y + 3)) == 1
    assert chain.drop_place(QPoint(5, 100000)) == 2
