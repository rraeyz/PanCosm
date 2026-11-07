"""What the inputs and outputs of the steps are (AUT-1 items 1 and 3): one vocabulary for every step, a name
meaning the same everywhere ("images": the frames to measure); a name that means something else in one step is keyed
"step id.name". The kind says what the value is; a file or folder input given as a path must exist before the step
runs."""

from dataclasses import dataclass

from .params import QT_TRANSLATE_NOOP

EXISTING = ("file", "files", "folder")  # kinds whose paths are checked; "new_*" ones are written by the step


@dataclass(frozen=True)
class IO:
    kind: str  # file, files, folder, new_file, new_folder, xy, positions, sky, text, number, date, object
    label: str


INPUTS = {
    "arc": IO("file", QT_TRANSLATE_NOOP("Steps", "Arc frame")),
    "bands": IO("text", QT_TRANSLATE_NOOP("Steps", "Bands")),
    "blue": IO("file", QT_TRANSLATE_NOOP("Steps", "Blue frame")),
    "cache": IO("new_folder", QT_TRANSLATE_NOOP("Steps", "Folder for downloaded files")),
    "cache_file": IO("new_file", QT_TRANSLATE_NOOP("Steps", "File for the answers kept offline")),
    "comps_xy": IO("positions", QT_TRANSLATE_NOOP("Steps", "Comparison stars (x y)")),
    "coord": IO("sky", QT_TRANSLATE_NOOP("Steps", "Sky position of the target")),
    "date": IO("date", QT_TRANSLATE_NOOP("Steps", "Date of the night")),
    "dec": IO("number", QT_TRANSLATE_NOOP("Steps", "Declination (°)")),
    "destination": IO("new_file", QT_TRANSLATE_NOOP("Steps", "Output file")),
    "e_xy": IO("positions", QT_TRANSLATE_NOOP("Steps", "Extraordinary images (x y)")),
    "err": IO("object", QT_TRANSLATE_NOOP("Steps", "Errors")),
    "error": IO("object", QT_TRANSLATE_NOOP("Steps", "Velocity errors")),
    "error2": IO("object", QT_TRANSLATE_NOOP("Steps", "Velocity errors, second star")),
    "export_dir": IO("new_folder", QT_TRANSLATE_NOOP("Steps", "Folder for the exported files")),
    "expression": IO("text", QT_TRANSLATE_NOOP("Steps", "Band formula")),
    "stars_sky": IO("object", QT_TRANSLATE_NOOP("Steps", "The stars by the sky (RA, Dec)")),
    "extra_xy": IO("positions", QT_TRANSLATE_NOOP("Steps", "Check stars and other targets (x y)")),
    "field": IO("object", QT_TRANSLATE_NOOP("Steps", "Identified field")),
    "first_xy": IO("xy", QT_TRANSLATE_NOOP("Steps", "Position in the first frame (x y)")),
    "flat": IO("file", QT_TRANSLATE_NOOP("Steps", "Flat frame")),
    "flux": IO("object", QT_TRANSLATE_NOOP("Steps", "Flux")),
    "folder": IO("folder", QT_TRANSLATE_NOOP("Steps", "Folder of the night's frames")),
    "frames": IO("object", QT_TRANSLATE_NOOP("Steps", "Frames")),
    "green": IO("file", QT_TRANSLATE_NOOP("Steps", "Green frame")),
    "grid": IO("folder", QT_TRANSLATE_NOOP("Steps", "Folder of model spectra")),
    "guesses": IO("object", QT_TRANSLATE_NOOP("Steps", "Line identifications")),
    "image": IO("file", QT_TRANSLATE_NOOP("Steps", "Image")),
    "image_a": IO("file", QT_TRANSLATE_NOOP("Steps", "Image in the first filter")),
    "image_b": IO("file", QT_TRANSLATE_NOOP("Steps", "Image in the second filter")),
    "images": IO("files", QT_TRANSLATE_NOOP("Steps", "Images")),
    "last_xy": IO("xy", QT_TRANSLATE_NOOP("Steps", "Position in the last frame (x y)")),
    "library": IO("new_folder", QT_TRANSLATE_NOOP("Steps", "Library of standard spectra")),
    "light_curve": IO("file", QT_TRANSLATE_NOOP("Steps", "Light curve")),
    "light_ratio": IO("number", QT_TRANSLATE_NOOP("Steps", "Light ratio of the two stars")),
    "lights": IO("folder", QT_TRANSLATE_NOOP("Steps", "Folder of the lights")),
    "measures": IO("object", QT_TRANSLATE_NOOP("Steps", "Measures of the visual binary")),
    "minima": IO("object", QT_TRANSLATE_NOOP("Steps", "Times of minimum")),
    "name": IO("text", QT_TRANSLATE_NOOP("Steps", "Name")),
    "o_xy": IO("positions", QT_TRANSLATE_NOOP("Steps", "Ordinary images (x y)")),
    "operation": IO("text", QT_TRANSLATE_NOOP("Steps", "Operation")),
    "orbit": IO("object", QT_TRANSLATE_NOOP("Steps", "Spectroscopic orbit")),
    "others": IO("files", QT_TRANSLATE_NOOP("Steps", "Other images")),
    "output": IO("new_file", QT_TRANSLATE_NOOP("Steps", "Output file")),
    "output_dir": IO("new_folder", QT_TRANSLATE_NOOP("Steps", "Folder for masters and calibrated frames")),
    "ra": IO("number", QT_TRANSLATE_NOOP("Steps", "Right ascension (°)")),
    "raster": IO("file", QT_TRANSLATE_NOOP("Steps", "Raster image")),
    "red": IO("file", QT_TRANSLATE_NOOP("Steps", "Red frame")),
    "ref_image": IO("file", QT_TRANSLATE_NOOP("Steps", "Frame the stars were marked on")),
    "rv": IO("object", QT_TRANSLATE_NOOP("Steps", "Radial velocities")),
    "rv1": IO("object", QT_TRANSLATE_NOOP("Steps", "Radial velocities, first star")),
    "rv2": IO("object", QT_TRANSLATE_NOOP("Steps", "Radial velocities, second star")),
    "science": IO("file", QT_TRANSLATE_NOOP("Steps", "Science frame")),
    "site": IO("object", QT_TRANSLATE_NOOP("Steps", "Observatory site")),
    "source": IO("file", QT_TRANSLATE_NOOP("Steps", "File to copy")),
    "spectra": IO("files", QT_TRANSLATE_NOOP("Steps", "Spectra")),
    "spectrum": IO("file", QT_TRANSLATE_NOOP("Steps", "Spectrum")),
    "standard": IO("file", QT_TRANSLATE_NOOP("Steps", "Spectrum of the telluric standard")),
    "start": IO("object", QT_TRANSLATE_NOOP("Steps", "Starting values")),
    "sun": IO("file", QT_TRANSLATE_NOOP("Steps", "Solar spectrum")),
    "target": IO("text", QT_TRANSLATE_NOOP("Steps", "Target")),
    "target_xy": IO("xy", QT_TRANSLATE_NOOP("Steps", "Target position in the first frame (x y)")),
    "targets": IO("object", QT_TRANSLATE_NOOP("Steps", "Targets")),
    "template": IO("file", QT_TRANSLATE_NOOP("Steps", "Template spectrum")),
    "template2": IO("file", QT_TRANSLATE_NOOP("Steps", "Template of the second star")),
    "time": IO("object", QT_TRANSLATE_NOOP("Steps", "Times")),
    # the same name, another meaning in one step
    "sample.night.folder": IO("new_folder", QT_TRANSLATE_NOOP("Steps", "Folder for the practice data")),
}


# what the steps give; a name both taken and given (images, light_curve, spectrum, …) is described once, above
OUTPUTS = {
    "apertures": IO("object", QT_TRANSLATE_NOOP("Steps", "Measurements at each aperture radius")),
    "arcs": IO("files", QT_TRANSLATE_NOOP("Steps", "Calibrated arc frames")),
    "atmosphere": IO("object", QT_TRANSLATE_NOOP("Steps", "Stellar parameters")),
    "best": IO("object", QT_TRANSLATE_NOOP("Steps", "Best period")),
    "calibrated": IO("files", QT_TRANSLATE_NOOP("Steps", "Calibrated frames")),
    "neb": IO("object", QT_TRANSLATE_NOOP("Steps", "Nearby-eclipsing-binary check")),
    "transit": IO("object", QT_TRANSLATE_NOOP("Steps", "Transit fit")),
    "catalog": IO("object", QT_TRANSLATE_NOOP("Steps", "Catalogue magnitudes")),
    "catalogue": IO("object", QT_TRANSLATE_NOOP("Steps", "Catalogue stars")),
    "chart": IO("new_file", QT_TRANSLATE_NOOP("Steps", "Finder chart")),
    "classes": IO("object", QT_TRANSLATE_NOOP("Steps", "Spectral classes")),
    "clean_spectrum": IO("object", QT_TRANSLATE_NOOP("Steps", "Cleaned frequency spectrum")),
    "colour": IO("object", QT_TRANSLATE_NOOP("Steps", "Colour curve")),
    "combined": IO("new_file", QT_TRANSLATE_NOOP("Steps", "Combined spectrum")),
    "components": IO("files", QT_TRANSLATE_NOOP("Steps", "Spectra of the components")),
    "curves": IO("object", QT_TRANSLATE_NOOP("Steps", "Light curves")),
    "dark_scales": IO("object", QT_TRANSLATE_NOOP("Steps", "Dark scale factors")),
    "echelle": IO("new_file", QT_TRANSLATE_NOOP("Steps", "Merged échelle spectrum")),
    "failed_masters": IO("object", QT_TRANSLATE_NOOP("Steps", "Masters that could not be made")),
    "fit": IO("object", QT_TRANSLATE_NOOP("Steps", "O−C fit")),
    "frequencies": IO("object", QT_TRANSLATE_NOOP("Steps", "Frequencies")),
    "good": IO("files", QT_TRANSLATE_NOOP("Steps", "Good frames")),
    "labelled": IO("object", QT_TRANSLATE_NOOP("Steps", "Labelled objects")),
    "masters": IO("files", QT_TRANSLATE_NOOP("Steps", "Master frames")),
    "maxima": IO("object", QT_TRANSLATE_NOOP("Steps", "Times of maximum")),
    "minimum": IO("object", QT_TRANSLATE_NOOP("Steps", "Time of minimum")),
    "missing": IO("object", QT_TRANSLATE_NOOP("Steps", "Missing calibration frames")),
    "model": IO("object", QT_TRANSLATE_NOOP("Steps", "Model fit")),
    "night": IO("object", QT_TRANSLATE_NOOP("Steps", "The night's plan")),
    "objects": IO("object", QT_TRANSLATE_NOOP("Steps", "Minor planets in the field")),
    "orders": IO("object", QT_TRANSLATE_NOOP("Steps", "Échelle orders")),
    "ok": IO("object", QT_TRANSLATE_NOOP("Steps", "Passed")),
    "path": IO("object", QT_TRANSLATE_NOOP("Steps", "Path")),
    "peaks": IO("object", QT_TRANSLATE_NOOP("Steps", "Highest peaks and their aliases")),
    "fap": IO("number", QT_TRANSLATE_NOOP("Steps", "False-alarm probability")),
    "periods": IO("object", QT_TRANSLATE_NOOP("Steps", "Periods")),
    "polarimetry": IO("object", QT_TRANSLATE_NOOP("Steps", "Polarisation")),
    "positions": IO("object", QT_TRANSLATE_NOOP("Steps", "Positions")),
    "power": IO("object", QT_TRANSLATE_NOOP("Steps", "Periodogram")),
    "problems": IO("object", QT_TRANSLATE_NOOP("Steps", "Problems found")),
    "product": IO("new_file", QT_TRANSLATE_NOOP("Steps", "Product image")),
    "quality": IO("object", QT_TRANSLATE_NOOP("Steps", "Frame quality")),
    "raw_converted": IO("files", QT_TRANSLATE_NOOP("Steps", "Camera raw files converted to FITS")),
    "report": IO("object", QT_TRANSLATE_NOOP("Steps", "Report")),
    "residual_spectrum": IO("object", QT_TRANSLATE_NOOP("Steps", "Residual frequency spectrum")),
    "rgb": IO("new_file", QT_TRANSLATE_NOOP("Steps", "Colour image")),
    "rms": IO("object", QT_TRANSLATE_NOOP("Steps", "Scatter of the residuals")),
    "rvs": IO("object", QT_TRANSLATE_NOOP("Steps", "Radial velocities")),
    "skipped": IO("object", QT_TRANSLATE_NOOP("Steps", "Spectra left out")),
    "solved": IO("new_file", QT_TRANSLATE_NOOP("Steps", "Plate-solved image")),
    "stack": IO("new_file", QT_TRANSLATE_NOOP("Steps", "Stacked image")),
    "stars": IO("object", QT_TRANSLATE_NOOP("Steps", "Stars")),
    "status": IO("object", QT_TRANSLATE_NOOP("Steps", "Status")),
    "t_ref": IO("object", QT_TRANSLATE_NOOP("Steps", "Reference time")),
    "telluric": IO("new_file", QT_TRANSLATE_NOOP("Steps", "Telluric-corrected spectrum")),
    "transformation": IO("object", QT_TRANSLATE_NOOP("Steps", "Transformation coefficients")),
    "truth": IO("object", QT_TRANSLATE_NOOP("Steps", "True values of the practice data")),
    "unsolved": IO("object", QT_TRANSLATE_NOOP("Steps", "Frames without a solution")),
    "variability": IO("object", QT_TRANSLATE_NOOP("Steps", "Variability of the stars")),
    "warnings": IO("object", QT_TRANSLATE_NOOP("Steps", "Warnings")),
    "window": IO("object", QT_TRANSLATE_NOOP("Steps", "Spectral window")),
    "written": IO("files", QT_TRANSLATE_NOOP("Steps", "Files written")),
    "zero_point": IO("object", QT_TRANSLATE_NOOP("Steps", "Zero point")),
}


def describe(step_id, name):
    """The IO of a step's input or output, or None for one not in the vocabulary (a plugin's)."""
    return INPUTS.get(f"{step_id}.{name}") or INPUTS.get(name) or OUTPUTS.get(name)


def check(step_id, inputs):
    """Raise ValueError naming the first file or folder input given as a path that does not exist."""
    from pathlib import Path

    from ..io import tpf

    for name, value in inputs.items():
        io = describe(step_id, name)
        if io is None or io.kind not in EXISTING:
            continue
        if io.kind == "folder" and isinstance(value, str):
            value = [f.strip() for f in value.split(";")]  # several folders, as the Calibration window gives them
        for path in value if isinstance(value, list | tuple) else [value]:
            if not isinstance(path, str | Path) or not str(path) or Path(path).exists():
                continue
            if io.kind == "folder":
                raise ValueError(f"folder not found: {path}")
            if not tpf.materialize(path):  # a frame of a pixel file is written when asked for
                raise ValueError(f"{name}: there is no {path}")
