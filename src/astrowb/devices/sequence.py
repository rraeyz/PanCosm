"""Imaging sequences: slew, filter, expose, save FITS with full headers; dithering through PHD2.

Headers carry everything the calibration and photometry steps read: IMAGETYP, EXPTIME,
DATE-OBS (UTC, exposure start), FILTER, XBINNING/YBINNING, CCD-TEMP, GAIN, OFFSET, READOUTM, OBJECT,
OBJCTRA/OBJCTDEC, SITELAT/SITELONG/SITEELEV, sub-frame origin (XORGSUBF/YORGSUBF), ROTATANG. Before every
exposure the observatory's abort flag is checked, so the supervisor stops a sequence within one exposure.

Focus: obs.focus = {"offsets": {"B": -30, ...}, "temp_coeff": -5.0, "temp_step": 0.5} (from the observatory
configuration). Changing filter moves the focuser by the difference of the two filters' offsets; during a
sequence the focuser follows the temperature (temp_coeff steps per degree, whenever the focuser's
temperature has changed by temp_step since the last correction).
"""

import re
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.time import Time

from .. import __version__
from .focus import hour_angle, needs_flip
from .observatory import Observatory, SafetyError


@dataclass
class Exposure:
    exptime: float
    count: int = 1
    filter: str | None = None
    binning: int = 1
    kind: str = "light"  # light | dark | bias | flat
    gain: int | None = None  # camera's own units; None: leave as it is
    offset: int | None = None
    readout: int | None = None  # index into the camera's ReadoutModes
    roi: list[int] | None = None  # [x, y, width, height] in binned pixels; None: full frame


@dataclass
class Target:
    name: str
    coord: SkyCoord | None  # None for darks/bias (no slew)
    exposures: list[Exposure] = field(default_factory=list)
    dither_every: int = 0  # frames; 0 = never
    start: Time | None = None  # wait until then (e.g. dusk, or before an eclipse)
    end: Time | None = None  # with an end, the exposure list repeats until then (time series)
    rotation: float | None = None  # rotator position angle (deg), if a rotator is connected


IMAGETYP = {"light": "Light Frame", "dark": "Dark Frame", "bias": "Bias Frame", "flat": "Flat Field"}


def _safe_name(text):
    return re.sub(r"[^A-Za-z0-9_+-]+", "_", text).strip("_") or "target"


def expose(obs: Observatory, exp: Exposure, poll_s=0.2, timeout_extra_s=120):
    """One exposure; returns (image as [y, x] array, start time ISO)."""
    if obs.abort.is_set():
        raise SafetyError("observatory unsafe: " + "; ".join(obs.reasons))
    for attr in ("BinX", "BinY"):
        obs.set("camera", attr, exp.binning)
    camera_settings(obs, exp)
    start = datetime.now(UTC)
    obs.call("camera", "StartExposure", exp.exptime, exp.kind in ("light", "flat"))
    deadline = time.monotonic() + exp.exptime + timeout_extra_s
    while not obs.call("camera", "ImageReady"):
        if obs.abort.is_set():
            obs.call("camera", "AbortExposure")
            raise SafetyError("exposure aborted: " + "; ".join(obs.reasons))
        if time.monotonic() > deadline:
            raise RuntimeError("camera did not deliver the image in time")
        time.sleep(poll_s)
    image = np.asarray(obs.call("camera", "ImageArray")).T  # ASCOM ImageArray is [x][y]
    return image, start.isoformat(timespec="milliseconds").replace("+00:00", "")


def camera_settings(obs: Observatory, exp: Exposure):
    """Gain, offset, read-out mode and sub-frame (ASCOM names); the full frame when no sub-frame is asked."""
    for attr, value in (("Gain", exp.gain), ("Offset", exp.offset), ("ReadoutMode", exp.readout)):
        if value is not None:
            obs.set("camera", attr, int(value))
    if exp.roi:
        x, y, w, h = (int(v) for v in exp.roi)
    else:
        try:
            x, y = 0, 0
            w, h = obs.call("camera", "CameraXSize") // exp.binning, obs.call("camera", "CameraYSize") // exp.binning
        except Exception:  # a camera that does not report its size cannot have been sub-framed by us
            return
    for attr, value in (("StartX", x), ("StartY", y), ("NumX", w), ("NumY", h)):
        obs.set("camera", attr, value)


def header(obs: Observatory, target: Target, exp: Exposure, date_obs: str):
    h = fits.Header()
    h["IMAGETYP"] = IMAGETYP[exp.kind]
    h["EXPTIME"] = (exp.exptime, "exposure time (s)")
    h["DATE-OBS"] = (date_obs, "UTC start of exposure")
    h["OBJECT"] = target.name
    h["XBINNING"] = h["YBINNING"] = exp.binning
    if exp.filter:
        h["FILTER"] = exp.filter
    for key, attr in (("CCD-TEMP", "CCDTemperature"), ("GAIN", "Gain"), ("OFFSET", "Offset")):
        try:
            h[key] = obs.call("camera", attr)
        except Exception:  # optional camera properties
            pass
    if exp.readout is not None:
        try:
            h["READOUTM"] = str(list(obs.call("camera", "ReadoutModes"))[exp.readout])
        except Exception:
            h["READOUTM"] = exp.readout
    if exp.roi:
        h["XORGSUBF"], h["YORGSUBF"] = (int(exp.roi[0]), "sub-frame origin x"), (int(exp.roi[1]), "sub-frame origin y")
    if target.rotation is not None and "rotator" in obs.devices:
        try:
            h["ROTATANG"] = (float(obs.call("rotator", "Position")), "rotator position angle (deg)")
        except Exception:
            pass
    if target.coord is not None:
        h["OBJCTRA"] = target.coord.ra.to_string(unit="hourangle", sep=" ", precision=1)
        h["OBJCTDEC"] = target.coord.dec.to_string(sep=" ", precision=0, alwayssign=True)
    loc = obs.location
    h["SITELAT"], h["SITELONG"], h["SITEELEV"] = loc.lat.deg, loc.lon.deg, loc.height.to_value("m")
    h["SWCREATE"] = f"astrowb {__version__}"
    return h


def move_focuser(obs: Observatory, steps, poll_s=0.2):
    """Relative move of an absolute focuser; waits until it stops."""
    steps = int(round(steps))
    if not steps or "focuser" not in obs.devices:
        return
    obs.call("focuser", "Move", int(obs.call("focuser", "Position")) + steps)
    while obs.call("focuser", "IsMoving"):
        time.sleep(poll_s)


def set_filter(obs: Observatory, name):
    if not name or "filterwheel" not in obs.devices:
        return
    names = list(obs.call("filterwheel", "Names"))
    if name not in names:
        raise ValueError(f"filter {name} is not in the wheel {names}")
    pos = obs.call("filterwheel", "Position")
    old = names[pos] if 0 <= pos < len(names) else None
    if old == name:
        return
    obs.set("filterwheel", "Position", names.index(name))
    while obs.call("filterwheel", "Position") == -1:  # -1 while moving
        time.sleep(0.2)
    offsets = getattr(obs, "focus", {}).get("offsets") or {}
    if old is not None and offsets:
        delta = offsets.get(name, 0) - offsets.get(old, 0)
        if delta:
            obs.note(f"focus offset {old} -> {name}: {delta:+d} steps")
            move_focuser(obs, delta)


class TemperatureFocus:
    """Moves the focuser by temp_coeff steps per degree whenever the temperature changed by temp_step."""

    def __init__(self, obs: Observatory):
        cfg = getattr(obs, "focus", {}) or {}
        self.obs, self.coeff, self.step = obs, float(cfg.get("temp_coeff", 0.0)), float(cfg.get("temp_step", 0.5))
        self.last = None

    def __call__(self):
        if not self.coeff or "focuser" not in self.obs.devices:
            return
        try:
            t = float(self.obs.call("focuser", "Temperature"))
        except Exception:  # no temperature sensor: nothing to follow
            return
        if self.last is None:
            self.last = t
        elif abs(t - self.last) >= self.step:
            steps = round(self.coeff * (t - self.last))
            self.obs.note(f"temperature {self.last:.1f} -> {t:.1f} C: focuser {steps:+d} steps")
            move_focuser(self.obs, steps)
            self.last = t


def rotate_to(obs: Observatory, angle, poll_s=0.2, timeout_s=180):
    if angle is None or "rotator" not in obs.devices:
        return
    obs.call("rotator", "MoveAbsolute", float(angle))
    deadline = time.monotonic() + timeout_s
    while obs.call("rotator", "IsMoving"):
        if obs.abort.is_set():
            obs.call("rotator", "Halt")
            raise SafetyError("rotation aborted: " + "; ".join(obs.reasons))
        if time.monotonic() > deadline:
            raise RuntimeError("rotator did not reach its position in time")
        time.sleep(poll_s)


def _pier(obs):
    try:
        return obs.call("mount", "SideOfPier")
    except Exception:  # not a German equatorial mount, or not supported: no flips
        return None


def save(obs: Observatory, target: Target, exp: Exposure, image, date_obs, out_dir: Path, index: int) -> Path:
    """Write one frame with its full header; never overwrites a frame from an earlier run."""
    stem = f"{_safe_name(target.name)}_{exp.kind}_{exp.filter or 'none'}_{exp.exptime:g}s"
    path, k = out_dir / f"{stem}_{index:04d}.fits", index
    while path.exists():
        k += 1
        path = out_dir / f"{stem}_{k:04d}.fits"
    data = image.astype(np.float32) if image.dtype.kind == "f" else image.astype(np.int32)
    fits.PrimaryHDU(data, header(obs, target, exp, date_obs)).writeto(path, overwrite=False)
    obs.note(f"saved {path.name}")
    return path


def sky_flats(
    obs: Observatory,
    filter_name,
    count,
    out_dir,
    target_adu=25000.0,
    tolerance=0.3,
    bias_adu=0.0,
    min_exp=0.1,
    max_exp=30.0,
    first_exp=1.0,
    max_frames=None,
    progress=None,
):
    """Twilight sky flats: each exposure time is scaled from the previous frame so the median
    (minus bias_adu) approaches target_adu; frames within +-tolerance are kept, others discarded.
    Stops when count frames are kept, or when the sky is too bright/faint for min_exp..max_exp
    (evening and morning both work: the scaling follows the sky). The mount is not moved here;
    point it at the flat spot (Sun azimuth + 180 deg, altitude ~75 deg, Chromey & Hasselbacher 1996)
    first, tracking off, so stars trail and are rejected by the flat combine."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    set_filter(obs, filter_name)
    target = Target("skyflat", None)
    exptime, written, tries = float(first_exp), [], 0
    max_frames = max_frames or 4 * count + 10
    while len(written) < count and tries < max_frames:
        tries += 1
        exp = Exposure(round(exptime, 3), 1, filter_name, kind="flat")
        image, date_obs = expose(obs, exp)
        level = float(np.median(image)) - bias_adu
        if abs(level - target_adu) <= tolerance * target_adu:
            written.append(str(save(obs, target, exp, image, date_obs, out_dir, len(written) + 1)))
            if progress:
                progress(len(written) / count, Path(written[-1]).name)
        else:
            obs.note(f"sky flat {exp.exptime:g}s: level {level:.0f} ADU, outside target; adjusting")
        wanted = exptime * target_adu / max(level, 1.0)
        if wanted > max_exp * 1.5 and level < target_adu:
            obs.note("sky flats stopped: sky too faint for the longest exposure")
            break
        if wanted < min_exp / 1.5 and level > target_adu:
            obs.note("sky flats: sky too bright for the shortest exposure; waiting")
            time.sleep(10)  # evening: it will get darker
        exptime = float(np.clip(wanted, min_exp, max_exp))
    return written


def panel_flats(obs: Observatory, filter_name, count, out_dir, brightness=None, open_after=False, **kwargs):
    """Flats on a flat panel (Alpaca CoverCalibrator): close the cover, light the panel, take flats with the
    exposure adjusted to the target level (as sky_flats), then switch the panel off. The cover is opened
    again only when asked (open_after), e.g. before the night."""
    if "panel" not in obs.devices:
        raise RuntimeError("no flat panel connected")

    def state(attr):  # alpyca gives enums, other drivers plain numbers
        v = obs.call("panel", attr)
        return int(getattr(v, "value", v))

    def wait(attr, ready, timeout_s=120):
        deadline = time.monotonic() + timeout_s
        while state(attr) not in ready:
            if time.monotonic() > deadline:
                raise RuntimeError(f"flat panel: {attr} did not become ready")
            time.sleep(0.5)

    covered = state("CoverState") != 0  # ASCOM CoverStatus: 0 not present, 1 closed, 2 moving, 3 open
    if covered:
        obs.call("panel", "CloseCover")
        wait("CoverState", (1,))
    level = int(obs.call("panel", "MaxBrightness") if brightness is None else brightness)
    obs.call("panel", "CalibratorOn", level)
    try:
        wait("CalibratorState", (3,))  # ASCOM CalibratorStatus 3: ready
        obs.note(f"flat panel on at {level}")
        return sky_flats(obs, filter_name, count, out_dir, **kwargs)
    finally:
        obs.call("panel", "CalibratorOff")
        if covered and open_after:
            obs.call("panel", "OpenCover")


def tonight(obs: Observatory, sun_alt=None):
    """(start, end) of the current or coming night at the observatory: the Sun below sun_alt
    (default: the safety rule's sun_max_alt, so the night matches what the supervisor allows)."""
    from ..planning.visibility import Site, _crossings, night_grid, sun_altitude

    loc = obs.location
    site = Site("observatory", loc.lat.deg, loc.lon.deg, loc.height.to_value("m"))
    local = obs.now() + (loc.lon.deg / 360 - 0.5) * u.day  # local solar time minus 12 h: the evening's date
    level = obs.rules.sun_max_alt if sun_alt is None else sun_alt
    for days in (-1, 0):  # tonight, or the night still running since yesterday evening
        date = (local + days * u.day).datetime.date().isoformat()
        t = night_grid(site, date, 2.0)
        c = _crossings(t, sun_altitude(t, site), level)
        dusk, dawn = (c["down"][0] if c["down"] else None), (c["up"][0] if c["up"] else None)
        if dawn is not None and obs.now() < dawn:
            return dusk, dawn
    return dusk, dawn


def _wait_until(obs, when, wait):
    """Sleep until `when` (observatory clock), checking the abort flag."""
    while obs.now() < when:
        if obs.abort.is_set():
            raise SafetyError("observatory unsafe: " + "; ".join(obs.reasons))
        wait(min(30.0, max(0.1, (when - obs.now()).to_value("s"))))


def run(obs: Observatory, targets: list[Target], out_dir, guider=None, progress=None, flip_after_h=0.1, wait=None):
    """Run the sequence; returns the paths written. Stops cleanly (raises SafetyError) when unsafe.

    A target with `start` waits for it; a target with `end` repeats its exposure list until no further
    exposure fits before `end` (a time series through an eclipse or a whole night)."""
    wait = wait or time.sleep
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    total = sum(e.count for t in targets for e in t.exposures if t.end is None)
    for target in targets:
        if target.end is not None and obs.now() >= target.end:
            obs.note(f"{target.name}: window already over, skipped")
            continue
        if target.start is not None and obs.now() < target.start:
            obs.note(f"{target.name}: waiting until {target.start.isot[:19]} UTC")
            _wait_until(obs, target.start, wait)
        gem, flipped = False, True
        rotate_to(obs, target.rotation)
        if target.coord is not None:
            obs.slew(target.coord, poll_s=0.5)
            gem = _pier(obs) is not None
            flipped = hour_angle(obs, target.coord) > flip_after_h  # already west of the meridian
            if guider:
                guider.guide()
        n, done = 0, False
        temperature_focus = TemperatureFocus(obs)
        while not done:
            for exp in target.exposures:
                set_filter(obs, exp.filter)
                for _ in range(exp.count):
                    if target.end is not None and obs.now() + exp.exptime * u.s > target.end:
                        done = True  # the next exposure would end after the window
                        break
                    if target.coord is not None and needs_flip(obs, target.coord, gem, flipped, flip_after_h):
                        obs.note(f"meridian flip for {target.name}")
                        if guider:
                            guider.stop()
                        obs.slew(target.coord, poll_s=0.5)  # the mount changes pier side itself
                        flipped = True
                        if guider:
                            guider.guide()
                    temperature_focus()
                    image, date_obs = expose(obs, exp)
                    path = save(obs, target, exp, image, date_obs, out_dir, n + 1)
                    written.append(str(path))
                    n += 1
                    if progress:
                        if target.end is not None and target.start is not None:
                            span = (target.end - target.start).to_value("s")
                            frac = (obs.now() - target.start).to_value("s") / span
                        else:
                            frac = len(written) / max(total, len(written))
                        progress(min(1.0, frac), path.name)
                    if guider and target.dither_every and n % target.dither_every == 0:
                        guider.dither()
                if done:
                    break
            done = done or target.end is None or n == 0
    return written
