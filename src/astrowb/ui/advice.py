"""What to do about an engine message (plans/architecture.md ARC-13, reduced): one or two lines per template of
messages.TEMPLATES whose own text does not already say it. advice(message) gives the translated advice or "".
New entries follow the frequent errors first; messages that end with ": do this" need none.
"""

import re

from PySide6.QtCore import QT_TRANSLATE_NOOP, QCoreApplication

from .messages import _patterns, error_line

ADVICE = {
    # observatory and devices
    "safety monitor is not answering": QT_TRANSLATE_NOOP(
        "Advice",
        "Check the safety monitor's cable or network and its driver; the telescope stays parked until it answers.",
    ),
    "safety monitor reports unsafe": QT_TRANSLATE_NOOP(
        "Advice", "Wait until the weather clears, or check the monitor's limits in the observatory set-up."
    ),
    "{device} has not answered for {age} s": QT_TRANSLATE_NOOP(
        "Advice", "Check that the device is switched on and connected; restart its driver (INDI / ASCOM Alpaca)."
    ),
    "slew did not finish in time": QT_TRANSLATE_NOOP(
        "Advice", "Check that the mount is not blocked or parked and that its driver reports the slew, then try again."
    ),
    "no {device} connected": QT_TRANSLATE_NOOP(
        "Advice", "Add it in the observatory set-up (Observe window), then start the observatory again."
    ),
    "busy with {job}": QT_TRANSLATE_NOOP("Advice", "Wait until it finishes, or stop it in the Observe window first."),
    "aborted: resume first": QT_TRANSLATE_NOOP("Advice", "Press Resume in the Observe window when it is safe again."),
    "missing or wrong token": QT_TRANSLATE_NOOP(
        "Advice", "Copy the token from the observatory computer's set-up into the Observe window."
    ),
    "the site's latitude / longitude are missing or out of range": QT_TRANSLATE_NOOP(
        "Advice",
        "Enter the site in the observatory set-up: latitude −90 to 90°, longitude −180 to 180° (east positive).",
    ),
    "two devices for {device}": QT_TRANSLATE_NOOP("Advice", "Keep one device of each kind in the observatory set-up."),
    "{device}: property {name} not available": QT_TRANSLATE_NOOP(
        "Advice", "The driver does not offer it: check the driver's version and settings."
    ),
    "no stars": QT_TRANSLATE_NOOP(
        "Advice", "Check the focus, the exposure time, and that the dome slit and cover are open."
    ),
    "stars blurred": QT_TRANSLATE_NOOP(
        "Advice", "Focus again (focus run in the Observe window), or check tracking and guiding."
    ),
    "few stars (clouds?)": QT_TRANSLATE_NOOP("Advice", "Look at the sky or the cloud sensor; wait, or expose longer."),
    "bright sky": QT_TRANSLATE_NOOP("Advice", "Twilight or moonlight: wait, or take the planned flats now."),
    "too few focus measurements": QT_TRANSLATE_NOOP(
        "Advice", "Widen the focus range or add steps, so that stars are measured on both sides of the best focus."
    ),
    "INDI server connection lost": QT_TRANSLATE_NOOP(
        "Advice", "Check the network and that indiserver is still running, then connect again."
    ),
    "PHD2 did not answer in time": QT_TRANSLATE_NOOP(
        "Advice", "Check that PHD2 is running with its server switched on (Tools → Enable Server)."
    ),
    "PHD2 connection lost: {error}": QT_TRANSLATE_NOOP(
        "Advice", "Check that PHD2 is still running with its server switched on, then connect again."
    ),
    "guiding did not settle: {error}": QT_TRANSLATE_NOOP(
        "Advice", "Check the guide star and the seeing; allow a larger settle distance if guiding is otherwise good."
    ),
    "camera did not deliver the image in time": QT_TRANSLATE_NOOP(
        "Advice", "Check the camera's cable and power, and restart its driver."
    ),
    "filter {name} is not in the wheel {names}": QT_TRANSLATE_NOOP(
        "Advice", "Use one of the wheel's filter names, or rename the filter in the wheel's driver."
    ),
    # calibration
    "frames have different sizes: {shapes}": QT_TRANSLATE_NOOP(
        "Advice",
        "Use frames of one camera with the same binning and sub-frame, or crop / bin them in the Images window.",
    ),
    "{name}: no EXPTIME": QT_TRANSLATE_NOOP(
        "Advice", "Add the exposure time with the header editor of the Images window (keyword EXPTIME, in seconds)."
    ),
    "darks with different exposure times cannot be combined: {times}": QT_TRANSLATE_NOOP(
        "Advice", "Keep darks of one exposure time together, or add bias frames so that darks can be scaled."
    ),
    "{name}: flat level {level} is not positive": QT_TRANSLATE_NOOP(
        "Advice", "Check the flat's exposure (it may be empty) and that the right bias and dark were subtracted."
    ),
    "the image has no valid pixels": QT_TRANSLATE_NOOP(
        "Advice", "The frame is empty (only NaN): check the file, or the processing that made it."
    ),
    # solving and catalogues
    "the stars of the frame do not match the Gaia stars around its pointing": QT_TRANSLATE_NOOP(
        "Advice",
        "Check the pointing (OBJCTRA / OBJCTDEC) and the pixel scale in the header, or plate-solve with ASTAP.",
    ),
    "the solver's output has no celestial WCS": QT_TRANSLATE_NOOP(
        "Advice", "The solver gave up: check its star database and the frame's pointing, then solve again."
    ),
    "solver did not finish within {timeout} s": QT_TRANSLATE_NOOP(
        "Advice",
        "Give the frame a pointing (OBJCTRA / OBJCTDEC) and a pixel scale, so the solver searches a small area.",
    ),
    "{server} did not answer within {seconds} s": QT_TRANSLATE_NOOP(
        "Advice", "The service may be busy or the network slow: try again later."
    ),
    "only {n} stars found in the image: too few to refine the plate solution": QT_TRANSLATE_NOOP(
        "Advice", "Use a longer exposure or a frame with more stars."
    ),
    "only {n} stars match Gaia DR3: too few to refine the plate solution": QT_TRANSLATE_NOOP(
        "Advice", "Check that the plate solution is roughly right (solve again) and that the stars are not trailed."
    ),
    "SIMBAD does not know '{name}'": QT_TRANSLATE_NOOP(
        "Advice", "Check the spelling, or give the coordinates (e.g. 12 34 56.7 +45 06 07)."
    ),
    "cannot reach SIMBAD and '{name}' is not in the local cache ({error})": QT_TRANSLATE_NOOP(
        "Advice", "Check the internet connection, or give the coordinates yourself."
    ),
    "VSX does not know '{name}'": QT_TRANSLATE_NOOP(
        "Advice", "Check the spelling (e.g. 'V0523 Cas'), or enter the coordinates and the period yourself."
    ),
    "the NASA Exoplanet Archive does not know '{planet}'": QT_TRANSLATE_NOOP(
        "Advice",
        "Check the name (e.g. 'HAT-P-32 b', with the planet's letter), or enter T0, period and duration yourself.",
    ),
    "no {mission} light curves for {target}": QT_TRANSLATE_NOOP(
        "Advice", "That mission may not have observed the target: try another mission, or check the name."
    ),
    # photometry and light curves
    "too few frames with every star found to compare apertures": QT_TRANSLATE_NOOP(
        "Advice", "Leave out frames where a star is lost (clouds, frame edge), or mark brighter comparison stars."
    ),
    "fewer than 3 usable stars": QT_TRANSLATE_NOOP(
        "Advice", "Use frames with more stars (longer exposure, clearer sky)."
    ),
    "the airmass hardly changed during the series: no extinction from it": QT_TRANSLATE_NOOP(
        "Advice",
        "Observe the field over a wider range of altitudes, or use a typical extinction coefficient for the site.",
    ),
    "fewer than 5 stars found on the first frame": QT_TRANSLATE_NOOP(
        "Advice", "Put a frame with more stars first, or check its focus and exposure."
    ),
    "the meridian flip needs the times": QT_TRANSLATE_NOOP(
        "Advice", "Measure frames whose headers hold their observation time (DATE-OBS)."
    ),
    "join needs two nights or more": QT_TRANSLATE_NOOP("Advice", "Choose the light curves of at least two nights."),
    "no measurements in the file": QT_TRANSLATE_NOOP(
        "Advice", "Check that it is the right file and that its columns are the ones the Guide describes."
    ),
    "{name}: need at least a time and a value column": QT_TRANSLATE_NOOP(
        "Advice", "Save the table with a time column and a value column (CSV or text, one row per point)."
    ),
    "not a table with two columns (time or phase, flux)": QT_TRANSLATE_NOOP(
        "Advice", "Save the light curve as two columns, time (or phase) and flux, one row per point."
    ),
    "{name}: no cadence with a time and good quality": QT_TRANSLATE_NOOP(
        "Advice", "This file has no usable points: download another sector or another pipeline's light curve."
    ),
    # times of minimum, orbits
    "need at least 8 minima for a third-body orbit": QT_TRANSLATE_NOOP(
        "Advice", "Add more times of minimum spanning several years (your own and published ones)."
    ),
    "apsidal motion needs at least 3 primary and 3 secondary minima": QT_TRANSLATE_NOOP(
        "Advice", "Add secondary minima (type II) as well as primary ones."
    ),
    "need at least {n} minima": QT_TRANSLATE_NOOP("Advice", "Add more times of minimum."),
    "a visual orbit needs at least 7 measures (seven elements)": QT_TRANSLATE_NOOP(
        "Advice", "Add more measures of position angle and separation (e.g. from the WDS)."
    ),
    # spectroscopy
    "observed and template spectra hardly overlap": QT_TRANSLATE_NOOP(
        "Advice", "Choose a template that covers the spectrum's wavelengths, or a narrower velocity range."
    ),
    "the reference spectrum does not cover the observed one": QT_TRANSLATE_NOOP(
        "Advice", "Choose a reference spectrum that covers the same wavelengths."
    ),
    "{name}: no spectrum found": QT_TRANSLATE_NOOP(
        "Advice", "Check that the file holds a 1-D spectrum, or extract it first from the 2-D frame."
    ),
    # files, projects, automations
    "folder not found: {path}": QT_TRANSLATE_NOOP(
        "Advice", "Check that the drive is connected and that the folder was not moved or renamed."
    ),
    "project was written by a newer version (schema {version})": QT_TRANSLATE_NOOP(
        "Advice", "Update the application to open this project."
    ),
    "{step}: missing input(s): {names}": QT_TRANSLATE_NOOP(
        "Advice", "Fill in the inputs named here, then run it again."
    ),
    "unknown step {step} (a plugin that is not installed?)": QT_TRANSLATE_NOOP(
        "Advice", "Install the plugin that provides the step, or take the step out of the automation."
    ),
    "working offline: the answer of {service} is not in the cache": QT_TRANSLATE_NOOP(
        "Advice", "Turn off Settings → Work offline while connected, run it once, then it works offline too."
    ),
    "no GPU adapter": QT_TRANSLATE_NOOP(
        "Advice", "Every job runs on the CPU; a newer graphics driver may make the GPU usable."
    ),
}


def advice(message):
    """The translated advice for an engine message (English, as raised), or ""."""
    text = str(message)
    typed = re.fullmatch(r"([A-Z][A-Za-z]+): (.*)", text, re.S)
    text = typed[2] if typed else text
    for regex, template in _patterns():
        if template in ADVICE and regex.fullmatch(text):
            return QCoreApplication.translate("Advice", ADVICE[template])
    return ""


def for_trace(traceback_text):
    """The advice for a worker's failure, as a paragraph to append ("" when there is none)."""
    text = advice(error_line(traceback_text))
    return f"\n\n{text}" if text else ""
