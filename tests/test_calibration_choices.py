"""Calibration masters chosen by hand (the owner, 2026-11-13: what the program matches by itself the user can
decide): a light group takes the flat or dark the user names, or none; a file of another kind is refused."""

from astrowb.calibration.frames import Frame
from astrowb.calibration.matching import apply_choices, make_plan


def frame(path, kind, exptime=60.0, filt=None, temp=-10.0):
    return Frame(path, kind, exptime, filt, temp, (1, 1), (100, 100), "", None, None)


def test_choices_override_the_matches():
    frames = [frame("b1", "bias", 0), frame("b2", "bias", 0), frame("d60", "dark", 60),
              frame("d60w", "dark", 60, temp=0),
              frame("fR1", "flat", 2, "R"), frame("fR2", "flat", 2, "R"), frame("fV", "flat", 2, "V"),
              frame("l1", "light", 60, "R"), frame("l2", "light", 60, "V")]  # fmt: skip
    plan = make_plan(frames)
    auto = {e["light"]: dict(e) for e in plan.lights}
    assert auto["l1"]["flat"][-1] == "r" and auto["l2"]["flat"][-1] == "v"
    assert apply_choices(plan, frames, {"R": {"flat": "fV", "dark": "none"}, "*": {"dark": "d60w"}}) == []
    got = {e["light"]: e for e in plan.lights}
    assert got["l1"]["flat"][-1] == "v" and got["l1"]["dark"] is None  # R lights: the V flat, no dark, as chosen
    assert got["l2"]["dark"][-1] == 0 and got["l2"]["flat"][-1] == "v"  # the others: the warm dark, their own flat
    assert apply_choices(plan, frames, {"*": {"flat": "b1"}}) == [("l1", "flat", "b1"), ("l2", "flat", "b1")]


def test_masters_chosen_in_the_window(tmp_path, qapp):
    """The dialog lists each light filter with the night's bias, dark and flat groups; its choice is the step's use."""
    from astrowb.ui.master_choice import MasterChoice, groups

    frames = [frame("b1", "bias", 0), frame("fR1", "flat", 2, "R"), frame("fV", "flat", 2, "V"),
              frame("l1", "light", 60, "R"), frame("l2", "light", 60, "V")]  # fmt: skip
    dicts = [f.as_dict() for f in frames]
    assert [p for p, _ in groups(dicts)["flat"]] == ["fR1", "fV"]
    dlg = MasterChoice(dicts)
    box = dlg.boxes[("R", "flat")]
    box.setCurrentIndex(box.findData("fV"))
    dlg.boxes[("V", "bias")].setCurrentIndex(dlg.boxes[("V", "bias")].findData("none"))
    assert dlg.choice() == {"R": {"flat": "fV"}, "V": {"bias": "none"}}
    dlg.close()
