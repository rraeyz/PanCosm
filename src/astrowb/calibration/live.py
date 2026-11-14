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
from . import masters


class LiveCalibrator:
    def __init__(self, master_paths, output_dir, cosmic_rays=False, read_noise=10.0, divide_flat=True):
        from ..photometry.live import load_masters
        from .frames import classify

        self.masters = load_masters(master_paths)
        self.names = {}  # kind -> the master's file name, written into each light's CALB / CALD / CALF
        for p in master_paths:
            kind = classify(masters.load(p)[1], str(p))
            if kind in ("bias", "dark", "flat"):
                self.names[kind] = Path(p).name
        self.out = Path(output_dir)
        self.out.mkdir(parents=True, exist_ok=True)
        self.cosmic_rays, self.read_noise, self.divide_flat = cosmic_rays, read_noise, divide_flat
        self.seen = set()

    def process(self, path):
        from .steps import _remove_cosmic_rays

        light, header = masters.load(path)
        exptime = get(header, "EXPTIME", "EXPOSURE", default=0.0)
        b = self.masters.get("bias", (None, None))[0]
        d, dh = self.masters.get("dark", (None, None))
        f = self.masters.get("flat", (None, None))[0] if self.divide_flat else None
        data = masters.calibrate(light, exptime, b, d, dh, f)
        for kind in ("bias", "dark", "flat"):
            used = self.names.get(kind) if (kind != "flat" or f is not None) else None
            header[f"CAL{kind[0].upper()}"] = (used or "none", f"{kind} used for calibration")
        if self.cosmic_rays:
            data = _remove_cosmic_rays(data, header, self.read_noise)
        stem = re.sub(r"\.(fits?|fts)(\.gz|\.fz)?$", "", Path(path).name, flags=re.I)
        self.seen.add(str(Path(path).resolve()))
        return str(masters.save(self.out / f"{stem}.fits", data, header))

    def poll(self, folder):
        """Calibrate every FITS file in folder not processed yet (by name, oldest first); [calibrated paths]."""
        files = sorted((p for p in Path(folder).iterdir() if p.suffix.lower() in (".fits", ".fit", ".fts")),
                       key=lambda p: p.stat().st_mtime)  # fmt: skip
        return [self.process(p) for p in files if str(p.resolve()) not in self.seen]
