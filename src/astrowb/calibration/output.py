"""What a calibration run writes and how much disk it needs (plans/calibration.md CAL-14).

need = estimate(frames)           bytes: every light as float32 (each colour half the size for a split mosaic),
                                  one master per group of calibration frames, FITS headers and blocks
check_space(folder, need)         ValueError naming both numbers when the disk cannot hold it (with 10 % spare)
"""

import shutil
from pathlib import Path

BLOCK = 2880  # FITS writes in blocks of this many bytes
HEADER = 2 * BLOCK  # a calibrated frame's header with its history and provenance (measured)


def _fits_bytes(ny, nx, bytes_per_pixel=4):
    data = ny * nx * bytes_per_pixel
    return HEADER + -(-data // BLOCK) * BLOCK


def estimate(frames, split_colour=False):
    """Bytes the run will write: frames are scan records (dicts with kind, shape)."""
    total = 0
    groups = set()
    for f in frames:
        ny, nx = f.get("shape") or (0, 0)
        if f.get("kind") in ("light", "arc"):
            total += 4 * _fits_bytes(ny // 2, nx // 2) if split_colour else _fits_bytes(ny, nx)
        elif f.get("kind") in ("bias", "dark", "flat"):
            groups.add((f["kind"], tuple(f.get("shape") or ()), f.get("exptime"), f.get("filter")))
    for _kind, shape, *_ in groups:
        if len(shape) == 2:
            total += _fits_bytes(*shape)  # its master
    return total


def check_space(folder, need, spare=0.1):
    """Raise ValueError when folder's disk has less free space than need (+ spare); the free bytes otherwise."""
    folder = Path(folder)
    probe = folder
    while not probe.exists() and probe.parent != probe:
        probe = probe.parent
    free = shutil.disk_usage(probe).free
    if free < need * (1 + spare):
        raise ValueError(f"the calibrated frames need {need / 1e9:.1f} GB and the disk has {free / 1e9:.1f} GB free")
    return free
