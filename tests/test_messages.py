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
        found |= set(re.findall(r'progress\([^"\n]*, f?"([^"{]+)"\)', path.read_text(encoding="utf-8")))
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
    assert text.startswith("astropy.io.fits.verify.VerifyError:") and "'exptime' is not upper case" in text
