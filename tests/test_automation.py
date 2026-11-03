"""Automations: templates are valid, links/each/format strings feed the right values, runs go through workers."""

import pytest
from astropy.io import fits

from astrowb.engine import automation, steps
from astrowb.engine.core import Engine
from astrowb.engine.tasks import TaskQueue
from astrowb.ui.i18n import LANGUAGES


def test_templates_are_complete():
    found = automation.available()
    assert len([a for a in found if a["template"]]) >= 5
    for auto in found:
        for entry in auto["steps"]:
            steps.get(entry["step"])  # every step exists
        assert set(automation.needed(auto)) <= set(auto["inputs"])  # the template asks for everything it needs
        texts = [auto["name"], auto["description"]] + [spec.get("label") for spec in auto["inputs"].values()]
        for text in filter(None, texts):  # templates speak every interface language
            assert not isinstance(text, dict) or set(text) >= set(LANGUAGES), text
        for spec in auto["inputs"].values():
            assert spec["kind"] in automation.KINDS


def drive(auto, inputs, fake):
    """Run the call generator with fake step outputs; returns the calls made and the final data."""
    made, gen = [], automation.calls(auto, inputs)
    call = next(gen)
    try:
        while True:
            made.append(call)
            call = gen.send(fake(*call))
    except StopIteration as stop:
        return made, stop.value


def test_each_format_and_pluck():
    auto = automation.load(automation.TEMPLATES / "40-spectroscopy-rv.json")
    inputs = {
        "science": ["/n/a.fits", "/n/b.fits.gz"],
        "arc": "/n/arc.fits",
        "guesses": [[1, 2], [3, 4]],
        "output_dir": "/out",
        "template": "/t.fits",
        "site": {"name": "s", "lat": 39.9, "lon": 32.8, "height": 900},
    }

    def fake(step_id, args, params):
        if step_id == "spectroscopy.reduce":
            return {"spectrum": {"path": args["output"], "science": args["science"], "arc": args["arc"]}}
        if step_id == "spectroscopy.rv":
            return {"rvs": [{"bjd": 10.0 + i, "rv": 5.0 * i, "rv_err": 0.1} for i, _ in enumerate(args["spectra"])]}
        return {"orbit": args}

    made, data = drive(auto, inputs, fake)
    assert [m[0] for m in made] == ["spectroscopy.reduce"] * 2 + ["spectroscopy.rv", "spectroscopy.orbit"]
    assert made[0][1]["science"] == "/n/a.fits" and made[0][1]["arc"] == "/n/arc.fits"
    assert made[2][1]["spectra"] == ["/out/a_1d.fits", "/out/b_1d.fits"]  # one output per item
    assert made[2][1]["site"] == inputs["site"]  # optional inputs are passed when the data has them
    assert made[3][1] == {"time": [10.0, 11.0], "rv": [0.0, 5.0], "error": [0.1, 0.1]}
    assert data["orbit"] == made[3][1]


def test_missing_inputs_and_unknown_steps():
    auto = automation.load(automation.TEMPLATES / "10-eclipsing-binary-night.json")
    assert automation.needed(auto) == ["folder", "output_dir", "target_xy"]
    with pytest.raises(steps.MissingInput, match="target_xy"):
        automation.check(auto, {"folder": "/a", "output_dir": "/b"})
    with pytest.raises(ValueError, match="unknown step"):
        automation.check({"steps": [{"step": "no.such"}]}, {})
    with pytest.raises(ValueError, match="no steps"):
        automation.check({"steps": []}, {})


def test_parse_kinds():
    assert automation.parse("xy", "12.5, 30") == [12.5, 30.0]
    assert automation.parse("pairs", "100 4000; 200 5000.5") == [[100, 4000], [200, 5000.5]]
    assert automation.parse("site", "39.9 32.8")["height"] == 0.0
    assert automation.parse("files", "a.fits; b.fits\nc.fits") == ["a.fits", "b.fits", "c.fits"]
    with pytest.raises(ValueError):
        automation.parse("xy", "1")


def test_save_load_and_run_through_workers(tmp_path, fits_file):
    auto = {
        "name": "copy twice",
        "steps": [
            {"step": "fits.save_as"},
            {"step": "fits.save_as", "inputs": {"source": "destination", "destination": "{second}"}},
        ],
    }
    path = automation.save(auto, automation.user_dir() / "copy.json")
    loaded = automation.load(path)
    assert [a["name"] for a in automation.available() if not a["template"]] == ["copy twice"]
    q = TaskQueue(max_workers=1)
    try:
        out = automation.run(
            Engine(queue=q),
            loaded,
            {"source": str(fits_file), "destination": str(tmp_path / "1.fits"), "second": str(tmp_path / "2.fits")},
        )
    finally:
        q.shutdown()
    assert out["destination"] == str(tmp_path / "2.fits") and fits.getheader(tmp_path / "2.fits")["OBJECT"] == "TEST"
