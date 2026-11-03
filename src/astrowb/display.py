"""Qt-free display stretch: float image -> uint8 for screen."""

import numpy as np


def _vis():  # astropy.visualization pulls in matplotlib: imported on the first image, not at start-up
    from astropy import visualization

    return visualization


INTERVALS = {
    "zscale": lambda: _vis().ZScaleInterval(),
    "minmax": lambda: _vis().MinMaxInterval(),
    "99.5%": lambda: _vis().PercentileInterval(99.5),
}
STRETCHES = {
    "linear": lambda: _vis().LinearStretch(),
    "sqrt": lambda: _vis().SqrtStretch(),
    "log": lambda: _vis().LogStretch(),
    "asinh": lambda: _vis().AsinhStretch(),
}


MAX_SAMPLES = 1_000_000  # limits are estimated on a regular subsample of large images
LUT_SIZE = 65536


def _sample(data: np.ndarray) -> np.ndarray:
    step = max(1, int(np.sqrt(data.size / MAX_SAMPLES)))
    sample = data[::step, ::step]
    return sample[np.isfinite(sample)]


def display_limits(data: np.ndarray, interval: str = "zscale") -> tuple[float, float]:
    """Black and white levels of an interval (zscale, minmax, 99.5%)."""
    sample = _sample(data)
    if sample.size == 0:
        return 0.0, 1.0
    lo, hi = INTERVALS[interval]().get_limits(sample)
    if interval == "minmax":  # extremes must come from every pixel, not a sample
        lo, hi = np.nanmin(data), np.nanmax(data)
    if not hi > lo:
        hi = lo + 1
    return float(lo), float(hi)


def to_display(data: np.ndarray, interval: str = "zscale", stretch: str = "linear", limits=None) -> np.ndarray:
    """Return a uint8 image, NaNs shown as black. Row 0 stays row 0 (caller flips for display).
    limits=(black, white) in data units overrides the interval (a manual screen stretch)."""
    if not np.isfinite(data).any():
        return np.zeros(data.shape, np.uint8)
    lo, hi = limits if limits else display_limits(data, interval)
    if not hi > lo:
        hi = lo + 1
    # Measured on 60 MP: evaluating log/asinh per pixel took 1-3 s; a 16-bit lookup table is far faster.
    lut = np.rint(STRETCHES[stretch]()(np.linspace(0, 1, LUT_SIZE), clip=True) * 255).astype(np.uint8)
    scaled = (data - np.float32(lo)) * np.float32((LUT_SIZE - 1) / (hi - lo))
    np.clip(scaled, 0, LUT_SIZE - 1, out=scaled)
    np.nan_to_num(scaled, copy=False, nan=0.0)
    return lut[scaled.astype(np.uint16)]


COLOUR_MAPS = ("grey", "heat", "viridis", "inferno", "magma", "cividis", "cool", "rainbow")
_MPL_NAMES = {"heat": "afmhot", "rainbow": "turbo"}


def colour_table(name: str = "grey", invert: bool = False) -> np.ndarray | None:
    """256 x 3 uint8 colours for the grey levels; None for plain grey (shown without a table)."""
    if name == "grey":
        table = None if not invert else np.repeat(np.arange(255, -1, -1, dtype=np.uint8)[:, None], 3, axis=1)
        return table
    from matplotlib import colormaps

    rgb = colormaps[_MPL_NAMES.get(name, name)](np.linspace(0, 1, 256))[:, :3]
    table = np.rint(rgb * 255).astype(np.uint8)
    return table[::-1].copy() if invert else table


def render(data, interval="zscale", stretch="linear", limits=None, cmap="grey", invert=False) -> np.ndarray:
    """The screen picture: uint8 grey (H x W) or RGB (H x W x 3), first row at the top (FITS y up)."""
    img8 = np.flipud(to_display(data, interval, stretch, limits))
    if cmap == "grey":
        return np.ascontiguousarray(255 - img8 if invert else img8)
    table = colour_table(cmap, invert)
    return np.ascontiguousarray(img8 if table is None else table[img8])


def save_picture(path, data, interval="zscale", stretch="linear", limits=None, cmap="grey", invert=False):
    """The image as shown (PNG / JPEG), or the data themselves as TIFF (32-bit float, FITS orientation flipped
    to image orientation) for other programs."""
    from pathlib import Path

    path = Path(path)
    if path.suffix.lower() in (".tif", ".tiff"):
        import tifffile

        tifffile.imwrite(path, np.flipud(np.asarray(data, np.float32)))
        return path
    from PIL import Image

    Image.fromarray(render(data, interval, stretch, limits, cmap, invert)).save(path, quality=95)
    return path
