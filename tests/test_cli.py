"""ARC-12: the command line runs steps and automations without the window, with clear exit codes."""

import io
import json

from astrowb import cli
from astrowb.__main__ import main


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    code = cli.main(list(argv), out, err)
    return code, out.getvalue(), err.getvalue()


def test_steps_and_help():
    code, out, _ = run("steps")
    assert code == 0 and "models.visual_orbit" in out and "calibration.run" in out
    assert all(len(line) < 160 for line in out.splitlines())
    code, out, _ = run("help", "models.visual_orbit")
    assert code == 0 and "inputs:      measures" in out and "parallax_mas = null" in out
    assert "measures  (object)  Measures of the visual binary" in out  # AUT-1: what each input is
    assert run("help", "no.such.step")[0] == cli.USAGE
    assert run("frobnicate")[0] == cli.USAGE


def visual_measures():
    from test_visual_orbit import simulate

    t, th, rho, s_r, s_t = simulate(n=25, seed=9)
    return "\n".join(f"{a:.4f} {b:.3f} {c:.4f} {d} {e}" for a, b, c, d, e in zip(t, th, rho, s_r, s_t, strict=True))


def test_run_a_step_with_inputs_and_parameters(tmp_path):
    from astrowb.engine.project import Project

    project = tmp_path / "p.astroproj"
    code, out, err = run("run", "models.visual_orbit", f"measures={visual_measures()}", "p_min=2", "p_max=60",
                         "--json", "--quiet", "--project", str(project))  # fmt: skip
    assert code == 0, err
    orbit = json.loads(out)["orbit"]
    assert 2 < orbit["P"] < 60 and err == ""
    with Project(project) as p:
        assert [r["step"] for r in p.runs()] == ["models.visual_orbit"]


def test_wrong_requests_and_failing_steps():
    code, _, err = run("run", "models.visual_orbit", "measures=x", "radius=3")
    assert code == cli.USAGE and "no input or parameter radius" in err
    assert run("run", "models.visual_orbit")[0] == cli.USAGE  # its input is missing
    assert run("run", "models.visual_orbit", "nonsense")[0] == cli.USAGE
    code, _, err = run("run", "models.visual_orbit", "measures=not numbers", "--quiet")
    assert code == cli.FAILED and err.startswith("failed: ")


def test_recipe_runs_an_automation(tmp_path):
    auto = {"name": "orbit", "steps": [{"step": "models.visual_orbit", "params": {"p_min": 2, "p_max": 60}}]}
    path = tmp_path / "orbit.json"
    path.write_text(json.dumps(auto))
    code, out, err = run("recipe", str(path), "--set", f"measures={visual_measures()}", "--json", "--quiet")
    assert code == 0, err
    assert "orbit" in json.loads(out)
    assert run("recipe", str(tmp_path / "missing.json"))[0] == cli.FAILED


def test_the_program_hands_its_commands_to_the_command_line(capsys):
    assert main(["help", "models.visual_orbit"]) == 0
    assert "measures" in capsys.readouterr().out
