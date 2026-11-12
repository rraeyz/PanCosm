"""VAL-8: the Automation window as a user goes through it: the eclipsing-binary template chosen from the list, its
inputs typed, Run, the time of minimum read from the result."""

import json

import pytest

from astrowb import sampledata


@pytest.mark.slow
@pytest.mark.parametrize("lang", ["en", "tr"])
def test_eclipsing_binary_template_on_the_practice_night(walk, tmp_path, lang):
    truth = sampledata.make(tmp_path / "night", n_lights=24)
    h = walk(lang)
    h.area("automation")
    page = h.page
    row = next(i for i, a in enumerate(page.found) if "10-eclipsing" in str(a["path"]))
    h.choose("list", row)
    h.type("edits.folder", str(tmp_path / "night" / "raw"))
    h.type("edits.output_dir", str(tmp_path / "cal"))
    h.type("edits.target_xy", "{:.0f} {:.0f}".format(*truth["target_xy"]))
    h.click("run_button")
    h.wait(lambda: bool(page.result.toPlainText()), timeout=300)
    h.check()
    out = json.loads(page.result.toPlainText())
    assert out["minimum"]["time"] == pytest.approx(truth["t_min_bjd_tdb"], abs=2 / 1440)
