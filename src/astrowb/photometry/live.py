"""Live light curve: frames are calibrated and measured as they arrive during the night.

The same per-frame method as light_curve() (frame-to-frame shift, re-centring, aperture photometry,
ensemble comparison), applied incrementally, so the cost per new frame is constant. Masters are the
files written by the Calibrate page (or any master bias/dark/flat); they are matched by IMAGETYP.
"""

import time
from pathlib import Path

import numpy as np

from .. import timing
from ..calibration.frames import classify
from ..calibration.masters import calibrate, load
from ..hdr import get
from .aperture import frame_shift, recenter
from .lightcurve import _measure_frame, target_coord
from .psf import neighbours_setup

FITS_SUFFIXES = (".fits", ".fit", ".fts")


def ready_files(folder, seen, min_age_s=2.0, now=None):
    """New FITS files in folder, oldest first, skipping ones written less than min_age_s ago
    (the camera may still be writing them)."""
    now = time.time() if now is None else now
    out = []
    for p in Path(folder).iterdir():
        if p.suffix.lower() in FITS_SUFFIXES and str(p) not in seen:
            try:
                mtime = p.stat().st_mtime
            except OSError:
                continue
            if now - mtime >= min_age_s:
                out.append((mtime, str(p)))
    return [p for _, p in sorted(out)]


def load_masters(paths):
    """{kind: (data, header)} for master bias / dark / flat files (kind from the header)."""
    masters = {}
    for p in paths or []:
        data, header = load(p)
        kind = classify(header, str(p))
        if kind in ("bias", "dark", "flat"):
            masters[kind] = (data, header)
    return masters


class LiveLightCurve:
    def __init__(self, target_xy, comps_xy, r_ap, r_in, r_out, coord=None, gain=None, box=11, masters=None, **method):
        """method: psf, remove_neighbours, sky_method, centring — light_curve's own per-frame code (PHO-19)."""
        self.xy = np.array([target_xy, *comps_xy], dtype=float)
        self.psf = bool(method.get("psf"))
        self.remove_neighbours = bool(method.get("remove_neighbours")) and not self.psf
        self.opts = {
            "sky_method": method.get("sky_method", "median"),
            "fixed": (),
            "centring": method.get("centring", "auto"),
        }
        self.r = (r_ap, r_in, r_out)
        self.coord, self.gain, self.box = coord, gain, box
        self.masters = masters or {}
        self.prev = None
        self.sky = self.where = None
        self.points = []  # dicts, one per frame
        self.failed = {}  # file -> reason

    def _frame(self, path):
        data, h = load(path)
        if self.masters:
            exptime = get(h, "EXPTIME", "EXPOSURE", default=0.0)
            dark = self.masters.get("dark")
            data = calibrate(
                data,
                exptime,
                self.masters.get("bias", (None,))[0],
                None if dark is None else dark[0],
                None if dark is None else dark[1],
                self.masters.get("flat", (None,))[0],
            )
        return data, h

    def add(self, path):
        """Measure one new frame; returns its point (dict) or None when it could not be measured."""
        try:
            data, h = self._frame(path)
            if self.prev is None:  # the first frame: positions are the clicked ones
                self.sky = target_coord(h, self.coord)
                self.where = timing.location(h)
                g = self.gain or get(h, "EGAIN", "GAIN", default=1.0) or 1.0
                self.gain = float(g)
                shift = (0.0, 0.0)
                self.xy = recenter(data, self.xy, self.box, max_move=self.box / 2)  # snap the clicks onto the stars
                self.ref, self.ref_path = data, str(path)
                if self.remove_neighbours:
                    self.opts["neighbours"] = neighbours_setup(data, self.xy, len(self.xy) - 1, self.r[2])
            else:  # against the first frame, as light_curve does: one bad frame does not carry on to the rest
                shift = frame_shift(self.ref, data)
            pred = self.xy + shift
            xy, flux, err, *_, lost = _measure_frame(
                data, h, pred, self.xy, self.r, self.gain, self.box, None, self.psf, len(pred) - 1, self.ref_path,
                opts=self.opts,
            )  # fmt: skip
            if lost:  # as the night run: a frame without its target or a comparison star is left out, with why
                self.failed[str(path)] = " ".join(str(x) for x in lost)
                return None
            t = timing.mid_time(h)
        except Exception as e:  # a bad frame (clouds, truncated file) must not stop the night
            self.failed[str(path)] = f"{type(e).__name__}: {e}"
            return None
        self.prev = data
        comp = flux[1:].sum()
        rel = flux[0] / comp
        rel_err = abs(rel) * np.sqrt((err[0] / flux[0]) ** 2 + (err[1:] ** 2).sum() / comp**2)
        if self.sky is not None:
            tv, scale = float(timing.bjd_tdb(t, self.sky, self.where).jd), "BJD_TDB"
        else:
            tv, scale = float(t.utc.jd), "JD_UTC"
        point = {
            "file": Path(path).name,
            "time": tv,
            "time_scale": scale,
            "jd_utc": float(t.utc.jd),
            "rel_flux": float(rel),
            "rel_flux_err": float(rel_err),
            "target_flux": float(flux[0]),
            "comp_flux": flux[1:].tolist(),
            "xy": xy.tolist(),
        }
        self.points.append(point)
        return point

    def light_curve(self):
        """The points so far in the format of light_curve() (for minima, export, AAVSO)."""
        pts = self.points
        out = {
            key: [p[key] for p in pts]
            for key in ("file", "time", "jd_utc", "rel_flux", "rel_flux_err", "target_flux", "comp_flux", "xy")
        }
        out["time_scale"] = pts[0]["time_scale"] if pts else "JD_UTC"
        out["coord"] = self.sky.to_string("hmsdms") if self.sky is not None else None
        return out
