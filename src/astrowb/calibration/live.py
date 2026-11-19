"""Calibrate frames as they arrive (plans/calibration.md CAL-22; AstroImageJ's Data Processor polling, MaxIm DL's
calibrate on acquire): the night's masters are read once, each new light is calibrated the way the batch run
calibrates it (the same calls, so a replayed night gives the same files) and handed on.

    live = LiveCalibrator(["master_bias_00.fits", "master_dark_01.fits", "master_flat_02.fits"], "out/")
    path = live.process("new_light.fits")        the calibrated file's path
    new = live.poll("incoming/")                  every light not seen yet, calibrated, oldest first
"""

import re
from pathlib import Path

from ..hdr import get
from ..photometry.planes_use import read as read_planes
from . import library_use, masters, planes_out


class LiveCalibrator:
    def __init__(
        self, master_paths, output_dir, cosmic_rays=False, read_noise=10.0, divide_flat=True, params=None, library=None
    ):
        from ..photometry.live import load_masters
        from .frames import classify

        self.masters = load_masters(master_paths)
        self.library = library_use.open_library(library)  # CAL-7: kinds the run gave no master of
        self.var = {}  # kind -> the master's VAR extension (batch run, write_planes on); a master without one counts 0
        self.names = {}  # kind -> the master's file name, written into each light's CALB / CALD / CALF
        for p in master_paths:
            kind = classify(masters.load(p)[1], str(p))
            if kind in ("bias", "dark", "flat"):
                self.names[kind] = Path(p).name
                if (v := read_planes(p)) is not None:
                    self.var[kind] = v[0]
        self.out = Path(output_dir)
        self.out.mkdir(parents=True, exist_ok=True)
        self.cosmic_rays, self.read_noise, self.divide_flat = cosmic_rays, read_noise, divide_flat
        self.params = {"read_noise": read_noise} | (params or {})  # write_planes, gain, saturation: as the batch run
        self.seen, self.cache = set(), {}

    def _for(self, light, header):
        """(masters, names, variances) for this light: the run's, and the library's for the kinds it lacks."""
        if self.library is None:
            return self.masters, self.names, self.var
        head = header.copy()
        head["NAXIS2"], head["NAXIS1"] = light.shape
        have, names, var = dict(self.masters), dict(self.names), dict(self.var)
        for kind, p in library_use.for_light(self.library, head, have).items():
            if p not in self.cache:  # each library master is read once
                self.cache[p] = (masters.load(p), read_planes(p))
            have[kind], names[kind] = self.cache[p][0], Path(p).name
            if self.cache[p][1] is not None:
                var[kind] = self.cache[p][1][0]
        return have, names, var

    def process(self, path):
        from .steps import _remove_cosmic_rays

        light, header = masters.load(path)
        exptime = get(header, "EXPTIME", "EXPOSURE", default=0.0)
        have, names, var = self._for(light, header)
        b = have.get("bias", (None, None))[0]
        d, dh = have.get("dark", (None, None))
        f = have.get("flat", (None, None))[0] if self.divide_flat else None
        data = masters.calibrate(light, exptime, b, d, dh, f)
        for kind in ("bias", "dark", "flat"):
            used = names.get(kind) if (kind != "flat" or f is not None) else None
            header[f"CAL{kind[0].upper()}"] = (used or "none", f"{kind} used for calibration")
        if self.cosmic_rays:
            data = _remove_cosmic_rays(data, header, self.read_noise)
        used = {
            k: (*have[k], var.get(k)) for k in ("bias", "dark", "flat") if k in have and (k != "flat" or f is not None)
        }
        stem = re.sub(r"\.(fits?|fts)(\.gz|\.fz)?$", "", Path(path).name, flags=re.I)
        self.seen.add(str(Path(path).resolve()))
        return planes_out.save(self.out / f"{stem}.fits", data, header, self.params, light, exptime, used)

    def poll(self, folder):
        """Calibrate every FITS file in folder not processed yet (by name, oldest first); [calibrated paths]."""
        files = sorted((p for p in Path(folder).iterdir() if p.suffix.lower() in (".fits", ".fit", ".fts")),
                       key=lambda p: p.stat().st_mtime)  # fmt: skip
        return [self.process(p) for p in files if str(p.resolve()) not in self.seen]
