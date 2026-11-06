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
    # photometry/steps.py
    QT_TRANSLATE_NOOP("Messages", "the target position {x}, {y} is outside the image ({nx} × {ny} px)"),
    QT_TRANSLATE_NOOP("Messages", "comparison star {n} at {x}, {y} is outside the image ({nx} × {ny} px)"),
    # photometry/catalog.py, steps.py
    QT_TRANSLATE_NOOP(
        "Messages",
        "no comparison star has a catalogue magnitude: plate-solve the first image, choose stars in APASS / Gaia",
    ),
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
    # photometry/steps.py, io/tpf.py (minima of a long series, target pixel files)
    QT_TRANSLATE_NOOP(
        "Messages", "no eclipse or transit stands out of the noise in this light curve: do the frames cover it?"
    ),
    QT_TRANSLATE_NOOP(
        "Messages",
        "the light curve shows {n} eclipses: give T0 and the period (e.g. from the period search) to time each one",
    ),
    QT_TRANSLATE_NOOP(
        "Messages",
        "no whole eclipse at the times predicted by T0 and the period: check T0, the period and the time scale",
    ),
    QT_TRANSLATE_NOOP("Messages", "{name}: no cadence with a time and good quality"),
    # timeseries/ephemeris.py
    QT_TRANSLATE_NOOP("Messages", "line {n}: '{value}' is not a time"),
    QT_TRANSLATE_NOOP("Messages", "need at least {n} minima"),
    # engine
    QT_TRANSLATE_NOOP("Messages", "{step}: missing input(s): {names}"),
    QT_TRANSLATE_NOOP("Messages", "the automation has no steps"),
    QT_TRANSLATE_NOOP("Messages", "unknown step {step} (a plugin that is not installed?)"),
    QT_TRANSLATE_NOOP("Messages", "no plate solver installed: install ASTAP (with a star database) or astrometry.net"),
    # io/fits.py
    QT_TRANSLATE_NOOP("Messages", "the keyword {key} describes the data and cannot be edited"),
    QT_TRANSLATE_NOOP("Messages", "the value of {key} must be plain ASCII text (FITS standard)"),
    # errors raised in the engine (shown when a task fails)
    # astrometry.py
    QT_TRANSLATE_NOOP("Messages", "the solver's output has no celestial WCS"),
    QT_TRANSLATE_NOOP("Messages", "solver did not finish within {timeout} s"),
    QT_TRANSLATE_NOOP("Messages", "{server} did not answer within {seconds} s"),  # mirrors.py
    # calibration/masters.py
    QT_TRANSLATE_NOOP(
        "Messages",
        "dark ({t_dark} s) without bias subtraction cannot be scaled to {exptime} s; add bias frames or darks with the same exposure",  # noqa: E501
    ),
    QT_TRANSLATE_NOOP("Messages", "linearity coefficients: give at least c0 and c1, with c1 > 0"),
    QT_TRANSLATE_NOOP("Messages", "frames have different sizes: {shapes}"),
    QT_TRANSLATE_NOOP(
        "Messages",
        "no frames to combine: check the folder and the frame types listed on the Calibrate page",
    ),
    QT_TRANSLATE_NOOP("Messages", "{name}: no EXPTIME"),
    QT_TRANSLATE_NOOP("Messages", "darks with different exposure times cannot be combined: {times}"),
    QT_TRANSLATE_NOOP("Messages", "{name}: flat level {level} is not positive"),
    # calibration/starmatch.py
    QT_TRANSLATE_NOOP(
        "Messages",
        "too few stars to match the frames: choose Align 'shift only', or use frames with more stars",
    ),
    QT_TRANSLATE_NOOP(
        "Messages",
        "the star patterns of the frames do not match: check that all frames show one field, or align by shift only",
    ),
    # compute/__init__.py
    QT_TRANSLATE_NOOP("Messages", "no GPU adapter"),
    QT_TRANSLATE_NOOP("Messages", "only a software adapter: {device}"),
    # devices/focus.py
    QT_TRANSLATE_NOOP("Messages", "too few focus measurements"),
    # devices/indi.py
    QT_TRANSLATE_NOOP("Messages", "INDI server connection lost"),
    QT_TRANSLATE_NOOP("Messages", "pier side not reported"),
    QT_TRANSLATE_NOOP("Messages", "{device} cannot bin"),
    QT_TRANSLATE_NOOP("Messages", "{device}: property {name} not available"),
    QT_TRANSLATE_NOOP("Messages", "{device}: {name} did not reach {states}"),
    # devices/phd2.py
    QT_TRANSLATE_NOOP("Messages", "PHD2 closed the connection"),
    QT_TRANSLATE_NOOP("Messages", "PHD2 did not answer in time"),
    QT_TRANSLATE_NOOP("Messages", "PHD2 connection lost: {error}"),
    QT_TRANSLATE_NOOP("Messages", "guiding did not settle: {error}"),
    # devices/pointing.py
    QT_TRANSLATE_NOOP("Messages", "not centred after {n} images ({error} arcsec off)"),
    QT_TRANSLATE_NOOP("Messages", "the three positions are too close together: turn the RA axis further"),
    # devices/sequence.py
    QT_TRANSLATE_NOOP("Messages", "filter {name} is not in the wheel {names}"),
    QT_TRANSLATE_NOOP("Messages", "camera did not deliver the image in time"),
    # devices/server.py
    QT_TRANSLATE_NOOP("Messages", "no {what} tonight at this site"),
    QT_TRANSLATE_NOOP("Messages", "request too large"),
    # engine/automation.py
    QT_TRANSLATE_NOOP("Messages", "{path}: not an automation (no step list)"),
    QT_TRANSLATE_NOOP("Messages", "two numbers expected: x y"),
    QT_TRANSLATE_NOOP("Messages", "pairs expected: a b; c d; ..."),
    QT_TRANSLATE_NOOP("Messages", "latitude longitude [height in m] expected"),
    # engine/builtin.py
    QT_TRANSLATE_NOOP("Messages", "unknown operation {op}"),
    # engine/project.py
    QT_TRANSLATE_NOOP("Messages", "project file must end with {extension}"),
    QT_TRANSLATE_NOOP("Messages", "project was written by a newer version (schema {version})"),
    # io/bayer.py
    QT_TRANSLATE_NOOP("Messages", "{name}: not a 2-D picture (shape {shape})"),
    QT_TRANSLATE_NOOP("Messages", "{name}: not a 2 x 2 Bayer sensor (e.g. Fujifilm X-Trans, Foveon)"),
    # io/fits.py
    QT_TRANSLATE_NOOP(
        "Messages",
        "no image data in file: open a FITS image, a picture or a camera raw file",
    ),
    QT_TRANSLATE_NOOP("Messages", "destination must differ from source"),
    # io/inspect.py
    QT_TRANSLATE_NOOP("Messages", "the rectangle is outside the image"),
    QT_TRANSLATE_NOOP("Messages", "the rectangle has no valid pixels"),
    # io/process.py
    QT_TRANSLATE_NOOP("Messages", "empty crop region"),
    QT_TRANSLATE_NOOP("Messages", "the factor must be positive"),
    QT_TRANSLATE_NOOP("Messages", "the image has no valid pixels"),
    QT_TRANSLATE_NOOP("Messages", "image too small for this box size"),
    QT_TRANSLATE_NOOP(
        "Messages",
        "the images do not have the same size: use frames of one camera and binning, or crop / bin them first",
    ),
    # models/data.py
    QT_TRANSLATE_NOOP("Messages", "{name}: need at least a time and a value column"),
    QT_TRANSLATE_NOOP("Messages", "not a table with two columns (time or phase, flux)"),
    # models/fit.py
    QT_TRANSLATE_NOOP("Messages", "give the period and the time of primary minimum"),
    # models/visual.py
    QT_TRANSLATE_NOOP("Messages", "a visual orbit needs at least 7 measures (seven elements)"),
    QT_TRANSLATE_NOOP("Messages", "no measures"),
    QT_TRANSLATE_NOOP("Messages", "each line needs epoch, position angle and separation"),
    # photometry/aperture.py
    QT_TRANSLATE_NOOP("Messages", "the telescope aperture and the exposure time must be positive"),
    # photometry/differential.py
    QT_TRANSLATE_NOOP("Messages", "too few points outside the left-out range to detrend"),
    # io/lzw.py
    QT_TRANSLATE_NOOP("Messages", "not a .Z (compress) file: check the file name, or download it again"),
    QT_TRANSLATE_NOOP("Messages", "unsupported .Z file: decompress it with gzip -d or 7-Zip and open the .fits"),
    QT_TRANSLATE_NOOP("Messages", "damaged .Z file: download it again"),
    QT_TRANSLATE_NOOP("Messages", "no spectrum covers the chosen wavelengths: widen the range or set it to 0 (all)"),
    QT_TRANSLATE_NOOP(
        "Messages", "{k} in the left-out range is far from its values at the fitted points: leave out only the eclipse"
    ),
    # photometry/export.py
    QT_TRANSLATE_NOOP("Messages", "give one catalogue magnitude per comparison star"),
    QT_TRANSLATE_NOOP("Messages", "star name, observer code and filter are required"),
    # photometry/polarimetry.py
    QT_TRANSLATE_NOOP("Messages", "need half-wave-plate angles that differ (e.g. 0, 22.5, 45, 67.5)"),
    # planning/targets.py
    QT_TRANSLATE_NOOP("Messages", "SIMBAD does not know '{name}'"),
    QT_TRANSLATE_NOOP("Messages", "cannot reach SIMBAD and '{name}' is not in the local cache ({error})"),
    # remotesensing/analysis.py
    QT_TRANSLATE_NOOP("Messages", "not allowed in an expression: {expr}"),
    QT_TRANSLATE_NOOP("Messages", "the two images are not on the same pixel grid"),
    QT_TRANSLATE_NOOP("Messages", "cannot read the expression: {error}"),
    QT_TRANSLATE_NOOP("Messages", "unknown band {band}; available: {bands}"),
    # remotesensing/raster.py
    QT_TRANSLATE_NOOP("Messages", "the files are not the same size: open bands of one scene at the same resolution"),
    QT_TRANSLATE_NOOP("Messages", "no image (2-D variable) in this file"),
    # spectroscopy/analysis.py
    QT_TRANSLATE_NOOP("Messages", "too few points in the window"),
    QT_TRANSLATE_NOOP("Messages", "too few points on one side of the line"),
    QT_TRANSLATE_NOOP("Messages", "no red emission peak above the continuum"),
    QT_TRANSLATE_NOOP("Messages", "pick at least two continuum points"),
    QT_TRANSLATE_NOOP("Messages", "the reference spectrum does not cover the observed one"),
    # spectroscopy/atmosphere.py
    QT_TRANSLATE_NOOP("Messages", "no grid spectra"),
    QT_TRANSLATE_NOOP("Messages", "the grid does not cover this spectrum's wavelengths"),
    QT_TRANSLATE_NOOP("Messages", "the grid has no complete box of points"),
    # spectroscopy/bf.py
    QT_TRANSLATE_NOOP("Messages", "observed and template spectra hardly overlap for this velocity range"),
    QT_TRANSLATE_NOOP("Messages", "the broadening function shows fewer than {n} peaks"),
    # spectroscopy/cube.py
    QT_TRANSLATE_NOOP("Messages", "the cube has no wavelength axis (CRVAL3 / CDELT3)"),
    QT_TRANSLATE_NOOP("Messages", "unknown wavelength unit {unit}"),
    QT_TRANSLATE_NOOP("Messages", "no 3-D data cube in this file"),
    # spectroscopy/disentangle.py
    QT_TRANSLATE_NOOP("Messages", "the spectra hardly overlap"),
    # spectroscopy/echelle.py
    QT_TRANSLATE_NOOP(
        "Messages",
        "no orders found: check that the flat shows the orders as bright stripes, or add them by hand on the flat",
    ),
    QT_TRANSLATE_NOOP("Messages", "identify at least four lines in at least two orders"),
    QT_TRANSLATE_NOOP("Messages", "order at row {row} could not be traced"),
    QT_TRANSLATE_NOOP("Messages", "too few lines matched: check the identified lines, order numbers and line list"),
    QT_TRANSLATE_NOOP("Messages", "at least two orders are needed to measure the scattered light"),
    # spectroscopy/rv.py
    QT_TRANSLATE_NOOP("Messages", "observed and template spectra hardly overlap"),
    QT_TRANSLATE_NOOP("Messages", "CCF peak at the edge of the velocity range: widen the range"),
    # spectroscopy/sb2.py
    QT_TRANSLATE_NOOP("Messages", "TODCOR peak at the edge of the velocity range: widen the range"),
    # spectroscopy/spectrum_io.py
    QT_TRANSLATE_NOOP("Messages", "{name}: no spectrum found"),
    QT_TRANSLATE_NOOP("Messages", "{name}: 1-D image without a wavelength solution (CRVAL1/CDELT1)"),
    # spectroscopy/steps.py
    QT_TRANSLATE_NOOP("Messages", "give a period guess (e.g. from the period search)"),
    # spectroscopy/longslit.py
    QT_TRANSLATE_NOOP(
        "Messages",
        "the spectrum could not be followed: for a faint one, give a brighter spectrum's row for its trace shape",
    ),
    QT_TRANSLATE_NOOP(
        "Messages",
        "the spectrum runs the other way on this frame: change 'Dispersion along' (rows / columns)",
    ),
    # spectroscopy/templates.py
    QT_TRANSLATE_NOOP("Messages", "the spectrum has no part with a clear signal to compare"),
    # spectroscopy/telluric.py
    QT_TRANSLATE_NOOP("Messages", "the spectrum does not cover a telluric band"),
    # spectroscopy/wavecal.py
    QT_TRANSLATE_NOOP("Messages", "identify at least two lines"),
    QT_TRANSLATE_NOOP("Messages", "too few lines matched: check the identified lines and the line list"),
    # spectroscopy/mkstandards.py
    QT_TRANSLATE_NOOP("Messages", "the MK standards cover 3800-5600 A: the spectrum has too little of that range"),
    QT_TRANSLATE_NOOP("Messages", "the MK standards could not be read from the download"),
    QT_TRANSLATE_NOOP("Messages", "no MK standards in the library folder"),
    # spectroscopy/reidentify.py and the Reduce tab
    QT_TRANSLATE_NOOP("Messages", "{name}: no identified lines (not an IRAF identify / ecidentify database?)"),
    QT_TRANSLATE_NOOP("Messages", "no IRAF database {name} next to it: choose the database file itself"),
    # timeseries/minima.py
    QT_TRANSLATE_NOOP("Messages", "the minimum must have data on both sides"),
    QT_TRANSLATE_NOOP(
        "Messages",
        "no minimum found: the window must hold one whole minimum with points on both sides",
    ),
    # timing.py
    QT_TRANSLATE_NOOP(
        "Messages",
        "no observation time in header (DATE-OBS, UT-OBS, JD, MJD-OBS): add DATE-OBS on the Images page's Header tab",
    ),
    QT_TRANSLATE_NOOP("Messages", "not an angle: {value}"),
    # updates.py
    QT_TRANSLATE_NOOP("Messages", "no GitHub repository configured for update checks"),
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
    QT_TRANSLATE_NOOP("Messages", "comparing with the MK standards"),
    QT_TRANSLATE_NOOP("Messages", "disentangling"),
    QT_TRANSLATE_NOOP("Messages", "band math"),
    QT_TRANSLATE_NOOP("Messages", "folder not found: {path}"),
    QT_TRANSLATE_NOOP("Messages", "{key} holds a date but no time of day, and no time keyword was found"),
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
    text = re.sub(r"^ValueError: ", "", text)  # Python's generic type says nothing to an observer; SafetyError etc. do
    return translate(text) if lines else ""
