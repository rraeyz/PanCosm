"""Plate solving with external, locally installed solvers: ASTAP or astrometry.net (solve-field).

Nothing is uploaded anywhere. The solver writes into a temporary folder (the input file is
never modified by the solver); the WCS keywords are then copied into our header.

ASTAP command line (hnsky.org/astap.htm): -f file -r radius_deg -fov height_deg (0 = auto)
-ra hours -spd dec+90 -z downsample (0 = auto) -wcs -o output_base; exit codes 0 solved,
1 no solution, 2 not enough stars, 16 image read error, 32/33 star database missing/unreadable.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from astropy.io import fits
from astropy.wcs import WCS

from .io.lzw import readable

ASTAP_ERRORS = {
    1: "no solution found",
    2: "not enough stars detected",
    16: "error reading the image",
    32: "no star database found (install one next to ASTAP, e.g. D50)",
    33: "error reading the star database",
}
_WCS_KEYS = (
    "CTYPE1",
    "CTYPE2",
    "CUNIT1",
    "CUNIT2",
    "CRPIX1",
    "CRPIX2",
    "CRVAL1",
    "CRVAL2",
    "CD1_1",
    "CD1_2",
    "CD2_1",
    "CD2_2",
    "CDELT1",
    "CDELT2",
    "CROTA1",
    "CROTA2",
    "PC1_1",
    "PC1_2",
    "PC2_1",
    "PC2_2",
    "EQUINOX",
    "RADESYS",
    "LONPOLE",
    "LATPOLE",
    "A_ORDER",
    "B_ORDER",
    "AP_ORDER",
    "BP_ORDER",
)


class SolveError(RuntimeError):
    pass


def find_solver() -> tuple[str, list[str]] | None:
    """(kind, argv prefix) of the first installed solver, or None."""
    for name in ("astap_cli", "astap"):
        exe = shutil.which(name)
        if exe:
            return "astap", [exe]
    if sys.platform == "win32":
        for base in (os.environ.get("ProgramFiles", r"C:\Program Files"), r"C:\Program Files (x86)"):
            for exe in ("astap_cli.exe", "astap.exe"):
                p = Path(base) / "astap" / exe
                if p.is_file():
                    return "astap", [str(p)]
    if sys.platform == "darwin" and Path("/Applications/ASTAP.app/Contents/MacOS/astap").is_file():
        return "astap", ["/Applications/ASTAP.app/Contents/MacOS/astap"]
    exe = shutil.which("solve-field")
    return ("astrometry.net", [exe]) if exe else None


def solve(
    path, solver=None, ra_deg=None, dec_deg=None, radius_deg=30.0, fov_deg=0.0, timeout=600, scale_arcsec=None
) -> fits.Header:
    """Return a header holding only the WCS solution of the image at path. scale_arcsec: the pixel scale when
    known (from the focal length and pixel size), which makes solving much faster."""
    solver = solver or find_solver()
    if solver is None:
        raise SolveError("no plate solver installed: install ASTAP (with a star database) or astrometry.net")
    kind, argv = solver
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "solution"
        if kind == "astap":
            cmd = argv + [
                "-f",
                str(path),
                "-r",
                str(radius_deg),
                "-fov",
                str(fov_deg),
                "-z",
                "0",
                "-wcs",
                "-o",
                str(base),
            ]
            if ra_deg is not None and dec_deg is not None:
                cmd += ["-ra", str(ra_deg / 15.0), "-spd", str(dec_deg + 90.0)]
        else:
            cmd = argv + [
                "--no-plots",
                "--no-remove-lines",  # these two steps need Python modules many installations lack (Debian, Ubuntu)
                "--uniformize",
                "0",
                "--overwrite",
                "--dir",
                tmp,
                "--out",
                "solution",
                "--new-fits",
                "none",
                "--cpulimit",
                str(timeout),
                str(path),
            ]
            if ra_deg is not None and dec_deg is not None:
                cmd += ["--ra", str(ra_deg), "--dec", str(dec_deg), "--radius", str(radius_deg)]
            if scale_arcsec:
                cmd += ["--scale-units", "arcsecperpix", "--scale-low", str(0.8 * scale_arcsec)]
                cmd += ["--scale-high", str(1.25 * scale_arcsec)]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise SolveError(f"solver did not finish within {timeout} s") from None
        wcs_file = base.with_suffix(".wcs")
        if kind == "astap" and proc.returncode != 0:
            raise SolveError(ASTAP_ERRORS.get(proc.returncode, f"ASTAP exit code {proc.returncode}"))
        if not wcs_file.is_file():
            raise SolveError("no solution found" + (f": {proc.stderr.strip()[-300:]}" if proc.stderr.strip() else ""))
        solved = _read_header(wcs_file)
    out = fits.Header()
    for key in _WCS_KEYS:
        if key in solved:
            out[key] = solved[key]
    for key in solved:  # SIP distortion terms
        if key[:2] in ("A_", "B_") or key[:3] in ("AP_", "BP_"):
            out[key] = solved[key]
    if not WCS(out).has_celestial:
        raise SolveError("the solver's output has no celestial WCS")
    cat = reference_catalogue(solved)
    if cat:
        out["ASTCAT"] = (cat, "star catalogue of the plate solution (ADES astCat)")
    return out


def reference_catalogue(solved):
    """ADES astCat of an astrometry.net solution, from the index it used ("index id: 4206"), or None. The index
    series are built from Tycho-2 (4100), 2MASS (4200) and Gaia DR2 (5000, 5200); an MPC report must name it."""
    for card in solved.cards:
        m = re.match(r"index id:\s*(\d+)", str(card.value)) if card.keyword in ("COMMENT", "HISTORY") else None
        if m:
            series = int(m.group(1)) // 100
            return {41: "Tyc2", 42: "2MASS", 50: "Gaia2", 52: "Gaia2"}.get(series)
    return None


def _read_header(path) -> fits.Header:
    """FITS-blocked header (astrometry.net, ASTAP -wcs) or ASTAP's plain-text variant (CR/LF lines)."""
    try:
        return fits.Header.fromfile(path)
    except Exception:
        return fits.Header.fromtextfile(path)


def apply_solution_header(h, wcs_header) -> None:
    """Replace the WCS (and SIP terms) in header h by wcs_header."""
    for key in list(h):  # remove an old solution first
        if key in _WCS_KEYS or key[:2] in ("A_", "B_") or key[:3] in ("AP_", "BP_") or key in ("ASTCAT", "ASTRNOTE"):
            del h[key]
    for key in ("PC1_1", "PC1_2", "PC2_1", "PC2_2", "CDELT1", "CDELT2"):  # astropy writes PC + CDELT, solvers CD
        h.remove(key, ignore_missing=True)
    h.update(wcs_header)


def apply_solution(path, wcs_header, solver_name="") -> None:
    """Write the WCS into the image's header (for calibrated products, not raw frames)."""
    with fits.open(readable(path), mode="update") as hdul:
        from .io.fits import find_image_hdu

        h = hdul[find_image_hdu(hdul)].header
        for key in list(h):  # remove an old solution first
            if key in _WCS_KEYS or key[:2] in ("A_", "B_") or key[:3] in ("AP_", "BP_"):
                del h[key]
        h.update(wcs_header)
        h.add_history(f"WCS from plate solving {solver_name}".strip())
