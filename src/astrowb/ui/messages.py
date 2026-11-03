"""Translation of messages that come from the engine and the observatory process.

Those parts have no Qt, so they speak English (their logs stay English, which helps support). The interface
matches each message against the English templates below and shows the translated template with the same
values. A template must equal the f-string that produces the message, with the values as {names}; a
{reasons} value is itself a "; "-separated list of messages. Unknown messages are shown as they are.
"""

import re
from functools import cache

from PySide6.QtCore import QT_TRANSLATE_NOOP, QCoreApplication

TEMPLATES = (
    # devices/safety.py
    QT_TRANSLATE_NOOP("Messages", "target is {sep} deg from the Sun (limit {limit})"),
    QT_TRANSLATE_NOOP("Messages", "the Sun is up ({alt} deg); daytime slews are not allowed"),
    QT_TRANSLATE_NOOP("Messages", "target altitude {alt} deg is below the limit {limit} deg at az {az}"),
    QT_TRANSLATE_NOOP("Messages", "the Sun is up ({alt} deg): night is over"),
    QT_TRANSLATE_NOOP("Messages", "the telescope points {sep} deg from the Sun"),
    QT_TRANSLATE_NOOP("Messages", "safety monitor is not answering"),
    QT_TRANSLATE_NOOP("Messages", "safety monitor reports unsafe"),
    QT_TRANSLATE_NOOP("Messages", "humidity sensor is not answering"),
    QT_TRANSLATE_NOOP("Messages", "windspeed sensor is not answering"),
    QT_TRANSLATE_NOOP("Messages", "rainrate sensor is not answering"),
    QT_TRANSLATE_NOOP("Messages", "cloudcover sensor is not answering"),
    QT_TRANSLATE_NOOP("Messages", "humidity {value} is above the limit {limit}"),
    QT_TRANSLATE_NOOP("Messages", "windspeed {value} is above the limit {limit}"),
    QT_TRANSLATE_NOOP("Messages", "rainrate {value} is above the limit {limit}"),
    QT_TRANSLATE_NOOP("Messages", "cloudcover {value} is above the limit {limit}"),
    QT_TRANSLATE_NOOP("Messages", "{device} has not answered for {age} s"),
    # devices/observatory.py, sequence.py, server.py
    QT_TRANSLATE_NOOP("Messages", "telescope is at altitude {alt} deg, below the limit"),
    QT_TRANSLATE_NOOP("Messages", "observatory is unsafe: {reasons}"),
    QT_TRANSLATE_NOOP("Messages", "observatory unsafe: {reasons}"),
    QT_TRANSLATE_NOOP("Messages", "slew aborted: {reasons}"),
    QT_TRANSLATE_NOOP("Messages", "exposure aborted: {reasons}"),
    QT_TRANSLATE_NOOP("Messages", "still unsafe: {reasons}"),
    QT_TRANSLATE_NOOP("Messages", "slew did not finish in time"),
    QT_TRANSLATE_NOOP("Messages", "no {device} connected"),
    QT_TRANSLATE_NOOP("Messages", "busy with {job}"),
    QT_TRANSLATE_NOOP("Messages", "aborted: resume first"),
    QT_TRANSLATE_NOOP("Messages", "missing or wrong token"),
    QT_TRANSLATE_NOOP("Messages", "not a frame written by the observatory"),
    # devices/sequence.py
    QT_TRANSLATE_NOOP("Messages", "no flat panel connected"),
    QT_TRANSLATE_NOOP("Messages", "flat panel: {state} did not become ready"),
    QT_TRANSLATE_NOOP("Messages", "rotator did not reach its position in time"),
    QT_TRANSLATE_NOOP("Messages", "rotation aborted: {reasons}"),
    # devices/setup.py
    QT_TRANSLATE_NOOP("Messages", "the site's latitude / longitude are missing or out of range"),
    QT_TRANSLATE_NOOP("Messages", "no safety monitor or weather sensor: the supervisor cannot see rain or clouds"),
    QT_TRANSLATE_NOOP("Messages", "{device}: no address"),
    QT_TRANSLATE_NOOP("Messages", "{device}: no INDI device name"),
    QT_TRANSLATE_NOOP("Messages", "{device}: only ASCOM Alpaca is supported for this device"),
    QT_TRANSLATE_NOOP("Messages", "two devices for {device}"),
    QT_TRANSLATE_NOOP(
        "Messages", "other computers may connect without encryption: turn on HTTPS unless the network is private"
    ),
    QT_TRANSLATE_NOOP("Messages", "https needs the observatory's certificate fingerprint"),
    QT_TRANSLATE_NOOP("Messages", "the observatory's certificate does not match (it shows {fp}…)"),
    # photometry/quality.py
    QT_TRANSLATE_NOOP("Messages", "no stars"),
    QT_TRANSLATE_NOOP("Messages", "stars blurred"),
    QT_TRANSLATE_NOOP("Messages", "few stars (clouds?)"),
    QT_TRANSLATE_NOOP("Messages", "bright sky"),
    # photometry/catalog.py, steps.py
    QT_TRANSLATE_NOOP("Messages", "no comparison star has a catalogue magnitude"),
    QT_TRANSLATE_NOOP("Messages", "the first image has no sky coordinates: plate-solve it first (Image menu)"),
    # engine/builtin.py
    QT_TRANSLATE_NOOP("Messages", "the image has no sky coordinates: plate-solve it first (Image menu)"),
    # photometry/steps.py (period search)
    QT_TRANSLATE_NOOP("Messages", "the light curve spans {hours} h: too short to search for periods"),
    # photometry/coefficients.py
    QT_TRANSLATE_NOOP("Messages", "fewer than 3 usable stars"),
    QT_TRANSLATE_NOOP("Messages", "the airmass hardly changed during the series: no extinction from it"),
    # photometry/fieldstars.py
    QT_TRANSLATE_NOOP("Messages", "fewer than 5 stars found on the first frame"),
    # photometry/moving.py
    QT_TRANSLATE_NOOP("Messages", "designation, observatory code and observer names are required"),
    # planning/ephemerides.py
    QT_TRANSLATE_NOOP("Messages", "VSX does not know '{name}'"),
    QT_TRANSLATE_NOOP("Messages", "the NASA Exoplanet Archive does not know '{planet}'"),
    # timeseries/archive.py
    QT_TRANSLATE_NOOP("Messages", "no {mission} light curves for {target}"),
    # timeseries/surveys.py
    QT_TRANSLATE_NOOP("Messages", "no measurements in the file"),
    QT_TRANSLATE_NOOP("Messages", "fewer than 3 measurements in band {band}"),
    # timeseries/oc_models.py
    QT_TRANSLATE_NOOP("Messages", "need at least 8 minima for a third-body orbit"),
    QT_TRANSLATE_NOOP("Messages", "apsidal motion needs at least 3 primary and 3 secondary minima"),
    # engine
    QT_TRANSLATE_NOOP("Messages", "{step}: missing input(s): {names}"),
    QT_TRANSLATE_NOOP("Messages", "the automation has no steps"),
    QT_TRANSLATE_NOOP("Messages", "unknown step {step} (a plugin that is not installed?)"),
    QT_TRANSLATE_NOOP("Messages", "no plate solver installed: install ASTAP (with a star database) or astrometry.net"),
    # io/fits.py
    QT_TRANSLATE_NOOP("Messages", "the keyword {key} describes the data and cannot be edited"),
    QT_TRANSLATE_NOOP("Messages", "the value of {key} must be plain ASCII text (FITS standard)"),
    # progress shown in the task list (ctx.progress in the steps)
    QT_TRANSLATE_NOOP("Messages", "reading headers"),
    QT_TRANSLATE_NOOP("Messages", "master bias"),
    QT_TRANSLATE_NOOP("Messages", "master dark"),
    QT_TRANSLATE_NOOP("Messages", "master flat"),
    QT_TRANSLATE_NOOP("Messages", "calibrating"),
    QT_TRANSLATE_NOOP("Messages", "combining"),
    QT_TRANSLATE_NOOP("Messages", "aligning"),
    QT_TRANSLATE_NOOP("Messages", "stacking"),
    QT_TRANSLATE_NOOP("Messages", "drizzle"),
    QT_TRANSLATE_NOOP("Messages", "reading"),
    QT_TRANSLATE_NOOP("Messages", "writing"),
    QT_TRANSLATE_NOOP("Messages", "plate solving"),
    QT_TRANSLATE_NOOP("Messages", "checking"),
    QT_TRANSLATE_NOOP("Messages", "simulating"),
    QT_TRANSLATE_NOOP("Messages", "photometry"),
    QT_TRANSLATE_NOOP("Messages", "quality"),
    QT_TRANSLATE_NOOP("Messages", "catalogue"),
    QT_TRANSLATE_NOOP("Messages", "astrometry"),
    QT_TRANSLATE_NOOP("Messages", "fit"),
    QT_TRANSLATE_NOOP("Messages", "trace"),
    QT_TRANSLATE_NOOP("Messages", "trace orders"),
    QT_TRANSLATE_NOOP("Messages", "extraction"),
    QT_TRANSLATE_NOOP("Messages", "arc"),
    QT_TRANSLATE_NOOP("Messages", "wavelength solution"),
    QT_TRANSLATE_NOOP("Messages", "downloading the template library"),
    QT_TRANSLATE_NOOP("Messages", "comparing"),
    QT_TRANSLATE_NOOP("Messages", "disentangling"),
    QT_TRANSLATE_NOOP("Messages", "band math"),
    QT_TRANSLATE_NOOP("Messages", "folder not found: {path}"),
    QT_TRANSLATE_NOOP("Messages", "give the target's name or coordinates"),
    QT_TRANSLATE_NOOP("Messages", "give the spectrograph's resolution R = lambda / delta lambda"),
    QT_TRANSLATE_NOOP("Messages", "the Sun"),
    QT_TRANSLATE_NOOP("Messages", "first estimate"),
)


@cache
def _patterns():
    out = []
    for template in TEMPLATES:
        regex = re.escape(template)
        for name in re.findall(r"\\\{(\w+)\\\}", regex):
            value = ".+?" if name == "reasons" else "[^;]+?"  # a single value never spans a "; " list
            regex = regex.replace(rf"\{{{name}\}}", rf"(?P<{name}>{value})", 1)
        out.append((re.compile(regex, re.S), template))
    return out


def translate(text: str) -> str:
    """The message in the interface language; parts it does not know stay as they are."""
    text = str(text)
    typed = re.fullmatch(r"([A-Z][A-Za-z]+): (.*)", text, re.S)
    if typed:  # "SafetyError: ..." -> the type stays, the message is translated
        return f"{typed[1]}: {translate(typed[2])}"
    for regex, template in _patterns():
        hit = regex.fullmatch(text)
        if hit:
            values = {k: translate(v) if k == "reasons" else v for k, v in hit.groupdict().items()}
            return QCoreApplication.translate("Messages", template).format(**values)
    if "; " in text:
        return "; ".join(translate(part) for part in text.split("; "))
    return text


def task_error(traceback_text: str) -> str:
    """The error itself from a worker's traceback (its "Type: message" line and the lines of a message that runs
    over several lines, at most ten), translated."""
    lines = [line for line in str(traceback_text).strip().splitlines() if line.strip()]
    frames = [i for i, line in enumerate(lines) if line.startswith(("Traceback", "  File "))]
    after = frames[-1] + 1 if frames else 0  # the error follows the last frame and its indented code line
    start = next((i for i in range(after, len(lines)) if not lines[i][:1].isspace()), len(lines) - 1)
    text = "\n".join(lines[start : start + 10])
    text = re.sub(
        r"^(?:[A-Za-z_]\w*\.)+(?=\w+:)", "", text
    )  # "astrowb.planning.targets.TargetError:" -> "TargetError:"
    return translate(text) if lines else ""
