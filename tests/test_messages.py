"""Engine and observatory messages are shown in the interface language: every real message matches a template."""

import astropy.units as u
import pytest
from astropy.coordinates import AltAz, SkyCoord
from test_observatory import NIGHT, SITE

from astrowb.devices.safety import Rules, check_link, check_sun, check_target, check_weather
from astrowb.engine import automation
from astrowb.engine.steps import MissingInput
from astrowb.ui import i18n
from astrowb.ui.messages import task_error, translate


@pytest.fixture
def turkish(qapp):
    translators = i18n.install(qapp, "tr")
    yield
    for t in translators:
        qapp.removeTranslator(t)


def at(alt, az, time):
    return SkyCoord(AltAz(alt=alt * u.deg, az=az * u.deg, obstime=time, location=SITE)).icrs


def real_messages():
    rules = Rules(max_cloud_cover=50)
    noon = NIGHT + 0.5 * u.day  # same site, midday
    out = check_weather(False, {"humidity": 95.0, "windspeed": "error", "rainrate": 1.0, "cloudcover": 80}, rules)
    out += check_weather(
        None, {"humidity": "error", "windspeed": 20.0, "rainrate": "error", "cloudcover": "error"}, rules
    )
    out += check_weather("error", {}, rules)
    out += check_link({"mount": 45.0}, rules)
    out += check_target(at(5, 0, noon), noon, SITE, rules)
    out += check_sun(at(60, 120, noon), noon, SITE, rules)
    out += [str(MissingInput("calibration.run", ["frames", "output_dir"]))]
    out += ["not a frame written by the observatory"]  # devices/server.py /file
    out += ["safety check sun and altitude failed: interpolating from IERS_Auto"]  # devices/observatory.py
    out += ["safety check failed: boom", "cannot evaluate the safety rules (boom): the telescope was not moved"]
    out += ["no flat panel connected", "flat panel: CoverState did not become ready"]  # devices/sequence.py
    out += ["rotator did not reach its position in time", "rotation aborted: safety monitor reports unsafe"]
    from astrowb.devices import setup

    bad = {"site": {}, "devices": {"mount": {"indi": ""}, "focuser": {"indi": "pi:7624"}, "rotator": {"indi": "a"}}}
    out += setup.problems(bad | {"listen": "0.0.0.0:11112"})
    out += ["https needs the observatory's certificate fingerprint"]  # devices/client.py
    out += ["no TESS light curves for AI Dra", "no ZTF light curves for AI Dra"]  # timeseries/archive.py, steps.py
    out += ["no measurements in the file", "fewer than 3 measurements in band V"]  # timeseries/surveys.py
    out += ["designation, observatory code and observer names are required"]  # photometry/moving.py
    out += ["fewer than 5 stars found on the first frame"]  # photometry/fieldstars.py
    out += ["fewer than 3 usable stars", "the airmass hardly changed during the series: no extinction from it"]
    out += ["the image has no sky coordinates: plate-solve it first (Image menu)"]  # engine/builtin.py
    out += ["the light curve spans 0.12 h: too short to search for periods"]  # photometry/steps.py
    out += ["the keyword NAXIS1 describes the data and cannot be edited"]  # io/fits.py
    out += ["the downloaded Earth-orientation table is too short: the server did not send the whole file"]
    out += ["this session belongs to the images window, not to the photometry window"]  # core/state.py
    out += ["this session was saved by a newer version of the application: update it to open it"]
    out += ["no way to read a session of version 1 of the photometry window"]
    out += ["no column flux in the table", "filter not understood: flux >", "cannot write tables as .fits"]
    out += ["the compiled routines are missing from this installation"]  # selfcheck.py
    from astrowb.timeseries.ephemeris import fit, parse_minima

    for call in (lambda: parse_minima("2460500.3 0.001 I\nabc"), lambda: fit(parse_minima("2460500.3"), 2460500, 1)):
        with pytest.raises(ValueError) as e:
            call()
        out.append(str(e.value))
    out += ["the value of SITE must be plain ASCII text (FITS standard)"]
    from astrowb.photometry.catalog import calibrate

    try:
        calibrate({"comp_flux": [[1.0]], "target_flux": [1.0]}, [None])
    except ValueError as e:
        out.append(str(e))
    out += ["the observatory's certificate does not match (it shows 0123456789abcdef…)"]
    try:
        setup.make_config({}, [{"kind": "mount", "protocol": "indi", "address": "a", "name": "m"}] * 2)
    except ValueError as e:
        out.append(str(e))
    for auto in ({"steps": []}, {"steps": [{"step": "no.such"}]}):
        with pytest.raises(ValueError) as e:
            automation.check(auto, {})
        out.append(str(e.value))
    return out


def test_every_real_message_is_translated(turkish):
    messages = real_messages()
    assert len(messages) >= 14
    for m in messages:
        assert translate(m) != m, m  # a changed f-string without its template would slip through here
    assert translate("the Sun is up (3.2 deg): night is over") == "Güneş doğdu (3.2 derece): gece bitti"


def test_nested_typed_and_unknown(turkish):
    text = "SafetyError: slew aborted: safety monitor reports unsafe; mount has not answered for 40 s"
    assert translate(text) == (
        "SafetyError: yönelme durduruldu: güvenlik izleyicisi güvensiz diyor; mount 40 sn'dir yanıt vermiyor"
    )
    assert translate("something new") == "something new"
    trace = 'Traceback (most recent call last):\n  File "x.py", line 1\nRuntimeError: busy with sequence\n'
    assert task_error(trace) == "RuntimeError: şu an meşgul: sequence"


def test_every_progress_word_has_a_template():
    import re
    from pathlib import Path

    from astrowb.ui.messages import TEMPLATES

    src = Path(__file__).parents[1] / "src" / "astrowb"
    found = set()
    for path in src.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        found |= set(re.findall(r'progress\([^"\n]*, f?"([^"{]+)"\)', text))
        found |= set(re.findall(r'pmap\([^"\n]*, ctx, "([^"{]+)"', text))  # labels the parallel map reports
    found |= {f"master {k}" for k in ("bias", "dark", "flat")}  # f"master {kinds[key]}"
    assert {"reading headers", "calibrating", "stacking"} <= found
    assert found - set(TEMPLATES) <= {"MCMC", "MAST", "k-means"}  # names, the same in every language


def test_task_error_keeps_a_message_over_several_lines():
    trace = (
        'Traceback (most recent call last):\n  File "x.py", line 1, in f\n    write()\n'
        "astropy.io.fits.verify.VerifyError: \nVerification reported errors:\nHDU 0:\n    Card 7:\n"
        "        Card keyword 'exptime' is not upper case.\nNote: astropy.io.fits uses zero-based indexing.\n"
    )
    text = task_error(trace)
    assert text.startswith("VerifyError:")  # no module path for the user and "'exptime' is not upper case" in text


def test_task_errors_do_not_show_module_paths():
    trace = (
        'Traceback (most recent call last):\n  File "x.py", line 1\n'
        "astrowb.planning.targets.TargetError: cannot reach SIMBAD and 'Vega' is not in the local cache\n"
    )
    assert task_error(trace).startswith("TargetError: cannot reach SIMBAD")


def test_every_engine_error_has_a_template():
    """A task that fails shows its error in the interface language: every message raised in the engine (literal
    or f-string) matches a template; developer errors (step definitions, plugin ids) and messages that are mostly
    values are left out."""
    import ast
    import re
    from pathlib import Path

    from astrowb.ui.messages import _patterns

    src = Path(__file__).parents[1] / "src" / "astrowb"
    skip = {"engine/steps.py", "engine/plugins.py", "cli.py"}  # cli.py: command-line usage, English only
    untranslated = []
    for path in src.rglob("*.py"):
        rel = path.relative_to(src).as_posix()
        if rel.startswith("ui/") or rel in skip:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not (isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call) and node.exc.args):
                continue
            kind = getattr(node.exc.func, "id", getattr(node.exc.func, "attr", ""))
            if kind in ("NotImplementedError", "AssertionError", "KeyError", "TypeError", "SystemExit"):
                continue
            arg = node.exc.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                text = arg.value
            elif isinstance(arg, ast.JoinedStr):
                text = "".join(v.value if isinstance(v, ast.Constant) else "X" for v in arg.values)
            else:
                continue
            if len(re.sub(r"[^A-Za-z]", "", text.replace("X", ""))) < 8:
                continue
            if not any(regex.fullmatch(text) for regex, _ in _patterns()):
                untranslated.append(f"{rel}:{node.lineno}: {text}")
    assert not untranslated, "\n".join(untranslated)


def test_no_translation_is_filed_without_a_context():
    """A tr() helper at module level made the translation tool file texts under an empty context, which the
    program never asks for: the 'Export results' button stayed English in every language."""
    import xml.etree.ElementTree as ET
    from pathlib import Path

    import astrowb

    for ts in (Path(astrowb.__file__).parent / "resources" / "i18n").glob("*.ts"):
        names = [c.findtext("name") for c in ET.parse(ts).getroot().iter("context")]
        assert all(names), ts.name


def test_task_error_drops_the_generic_value_error_name():
    trace = 'Traceback (most recent call last):\n  File "x.py", line 1, in f\n    g()\n'
    trace += "ValueError: identify at least two lines"
    assert task_error(trace) == "identify at least two lines"


def test_advice_belongs_to_real_templates_and_is_found_for_a_message():
    from astrowb.ui.advice import ADVICE, advice
    from astrowb.ui.messages import TEMPLATES

    assert len(ADVICE) >= 60 and not set(ADVICE) - set(TEMPLATES)
    assert advice("VSX does not know 'XX Zzz'").startswith("Check the spelling")
    assert advice("TargetError: SIMBAD does not know 'Vega X'").startswith("Check the spelling")
    assert advice("frames have different sizes: (10, 10), (20, 20)").startswith("Use frames of one camera")
    assert advice("something nobody wrote") == ""


def test_the_failure_dialog_gets_the_advice_of_a_worker_error():
    from astrowb.ui.advice import for_trace

    trace = (
        "Traceback (most recent call last):\n"
        '  File "x.py", line 1, in step\n'
        "    raise ValueError(...)\n"
        "ValueError: VSX does not know 'XX Zzz'\n"
    )
    assert for_trace(trace).startswith("\n\nCheck the spelling")
    assert for_trace("Traceback ...\nValueError: nothing known\n") == ""
