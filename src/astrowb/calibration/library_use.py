"""The library's masters in a run (plans/calibration.md CAL-7): a light whose night has no master of a kind gets the
library's `Library.best` of it when it is within its validity; an older one is not used, it is noted. The night's own
masters always win (this only looks at what `matching.make_plan` lists as missing).

    built = fill(plan, frames, folder)       plan.lights now name library masters; built: {key: (data, header, path)}
    n = add_masters(folder, masters)         the masters a run made, filed in the library
"""

from pathlib import Path

from ..core.errors import AppError
from .library import Library, _describe


def library_folder(settings):
    """Settings → Files, else the "masters" folder of the settings directory."""
    from ..settings import config_dir

    return str(settings.get("calibration.library_folder", "") or config_dir() / "masters")


def open_library(folder):
    """The Library at folder, or None when it has no index yet (a run never creates one)."""
    return Library(folder) if folder and (Path(folder) / "index.json").exists() else None


def pick(lib, kind, header):
    """(path of the fitting master or None, note or None): note = {"age", "used", "valid_days"}; an out-of-validity
    master is only noted."""
    m = lib.best(kind, header)
    if m is None:
        return None, None
    return (m["path"] if m["valid"] else None), {
        "age": m["age_days"],
        "used": m["valid"],
        "valid_days": lib.valid[kind],
    }


def shown_plan(frames):
    """The plan as the pages show it: the night's matches, then the library's for what is missing (nothing read)."""
    from ..settings import Settings
    from .matching import make_plan

    plan = make_plan(frames)
    fill(plan, frames, library_folder(Settings()), load=False)
    return plan


def _header(frame):
    from .steps import _frame_header

    h = _frame_header(frame.path)
    h["NAXIS2"], h["NAXIS1"] = frame.shape
    h["XBINNING"], h["YBINNING"] = frame.binning
    return h


def fill(plan, frames, folder, load=True):
    """Every (light, kind) the plan lists as missing is looked up in the library: a master within validity becomes
    the light's match (key (kind, "library", path)), the others stay missing; plan.library keeps a note for each
    master found. Returns {key: (data, header, path)} of the masters read (once each) when load, else {}."""
    lib = open_library(folder)
    if lib is None or not plan.missing:
        return {}
    from . import masters

    by_path, entries = {f.path: f for f in frames}, {e["light"]: e for e in plan.lights}
    heads, built, left = {}, {}, []
    for path, kind, why in plan.missing:
        if path not in heads:
            heads[path] = _header(by_path[path])
        found, note = pick(lib, kind, heads[path])
        if note:
            plan.library.append((path, kind, note))
        if not found:
            left.append((path, kind, why))
            continue
        key = (kind, "library", found)
        entries[path][kind] = key
        if load and key not in built:
            built[key] = (*masters.load(found), found)
    plan.missing = left
    return built


def for_light(lib, header, have):
    """{kind: path} of the library's valid masters for the kinds not in `have`; AppError when the light would get
    no master at all (the live follow skips it and says which kinds were missing)."""
    found = {k: p for k in ("bias", "dark", "flat") if k not in have and (p := pick(lib, k, header)[0])}
    if not found and not have:
        raise AppError("no master in the library fits this frame: no valid {kinds}", kinds="bias, dark, flat")
    return found


def add_masters(folder, paths):
    """The `master_<kind>_NN.fits` files of a run filed in the library (not twice); how many were new."""
    from astropy.io import fits

    lib, n = Library(folder), 0
    for p in paths:
        name = Path(p).name
        kind = name.split("_")[1] if name.startswith("master_") and name.count("_") >= 2 else ""
        if kind not in ("bias", "dark", "flat"):
            continue
        info = _describe(fits.getheader(p)) | {"kind": kind}
        if not any(all(e.get(k) == v for k, v in info.items()) for e in lib.entries):
            lib.add(p, kind)
            n += 1
    return n
