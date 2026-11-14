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
from ..calibration.stacking import follow_stars
from ..hdr import get
from .aperture import frame_shift, recenter, snap_to_star
from .differential import ensemble
from .lightcurve import SNR_FOUND, _measure_frame, target_coord
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


def _ensemble(pts):
    """Relative fluxes of the points against their comparison stars (differential.ensemble: a missing star's share
    taken from the frames that have them all)."""
    return ensemble([p["target_flux"] for p in pts], [p["target_flux_err"] for p in pts],
                    [p["comp_flux"] for p in pts], [p["comp_flux_err"] for p in pts])  # fmt: skip


class LiveLightCurve:
    def __init__(self, target_xy, comps_xy, r_ap, r_in, r_out, coord=None, gain=None, box=11, masters=None,
                 extra_xy=(), **method):  # fmt: skip
        """method: psf, remove_neighbours, sky_method, centring, track_stars, camera, header_time, shutter_delay —
        light_curve's own per-frame code
        (PHO-19); track_stars: stars picked on the first frame that place every frame (stacking.follow_stars);
        extra_xy: check stars and further targets, measured against the same comparison stars (as the night run)."""
        self.xy = np.array([target_xy, *comps_xy, *extra_xy], dtype=float)
        self.n_comp = len(comps_xy)
        self.psf = bool(method.get("psf"))
        self.remove_neighbours = bool(method.get("remove_neighbours")) and not self.psf
        self.opts = {
            "sky_method": method.get("sky_method", "median"),
            "fixed": (),
            "centring": method.get("centring", "auto"),
            "camera": method.get("camera"),  # read noise and dark current, as the night run (PHO-19)
        }
        self.time_rule = (method.get("header_time", "auto"), method.get("shutter_delay", 0.0))
        track = method.get("track_stars")
        self.track = np.asarray([] if track is None else track, float).reshape(-1, 2)
        self.place = (np.eye(2), np.zeros(2))
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
                if len(self.track):
                    self.track = snap_to_star(data, self.track, radius=5.0)
            elif len(self.track):  # placed by the stars the user picked, from where the last frame had them
                self.place = follow_stars(data, self.track, *self.place)
            else:  # against the first frame, as light_curve does: one bad frame does not carry on to the rest
                shift = frame_shift(self.ref, data)
            pred = self.xy @ self.place[0].T + self.place[1] if len(self.track) else self.xy + shift
            xy, flux, err, *_, lost = _measure_frame(
                data, h, pred, self.xy, self.r, self.gain, self.box, None, self.psf, self.n_comp, self.ref_path,
                opts=self.opts,
            )  # fmt: skip
            k = 1 + self.n_comp  # target, comparison stars, then the extra stars
            seen = np.divide(flux[1:k], err[1:k], out=np.zeros(k - 1), where=err[1:k] > 0) >= SNR_FOUND
            if lost and (lost[0] != "comparison" or not seen.any()):  # as the night run: no target, no comparison
                self.failed[str(path)] = " ".join(str(x) for x in lost)  # star at all, or not placed: left out
                return None
            flux, err = np.asarray(flux, float).copy(), np.asarray(err, float).copy()
            flux[1:k][~seen], err[1:k][~seen] = np.nan, np.nan  # measured against the comparison stars it has
            t = timing.mid_time(h, *self.time_rule)
        except Exception as e:  # a bad frame (clouds, truncated file) must not stop the night
            self.failed[str(path)] = f"{type(e).__name__}: {e}"
            return None
        self.prev = data
        pts = [*self.points, {"target_flux": flux[0], "target_flux_err": err[0], "comp_flux": flux[1:k].tolist(),
                              "comp_flux_err": err[1:k].tolist()}]  # fmt: skip
        rel, rel_err = (float(v[-1]) for v in _ensemble(pts))
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
            "target_flux_err": float(err[0]),
            "comp_flux": flux[1:k].tolist(),
            "comp_flux_err": err[1:k].tolist(),
            "extra_flux": flux[k:].tolist(),
            "extra_flux_err": err[k:].tolist(),
            "xy": xy.tolist(),
            "missing": [int(k) + 1 for k in np.flatnonzero(~seen)],  # 1-based, as the night run's "partial"
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
        if pts:  # every point again against the shares of the whole night so far, as the night run computes them
            rel, rel_err = _ensemble(pts)
            out["rel_flux"], out["rel_flux_err"] = rel.tolist(), rel_err.tolist()
        out["partial"] = {p["file"]: p["missing"] for p in pts if p["missing"]}
        if len(self.xy) > 1 + self.n_comp:  # the check stars, as the night run gives them (the window computes theirs)
            out["extra_flux"] = [p["extra_flux"] for p in pts]
            out["extra_flux_err"] = [p["extra_flux_err"] for p in pts]
        out["time_scale"] = pts[0]["time_scale"] if pts else "JD_UTC"
        out["coord"] = self.sky.to_string("hmsdms") if self.sky is not None else None
        return out
