"""Regenerates tests/validation/data/hatp32_iraf_phot.csv with IRAF 2.17 apphot.phot (plans/validation.md VAL-2).

    tools/reference_env.sh iraf     # once: IRAF and its NOAO packages (Debian / Ubuntu: apt)
    ASTROWB_VALIDATION_DATA=<folder containing HatP32Dec202017> python tests/validation/scripts/iraf/hatp32_phot.py

The centres are ours (the light curve's), so the comparison is of the photometry alone: apertures of 4 px, the sky
in a ring of 10–16 px, its median after 3-sigma rejection repeated 10 times, gain 1, no read noise. IRAF counts
pixels from 1, the table from 0. The flux error is IRAF's own formula (phot's merr, before it is turned into
magnitudes): sqrt(flux / epadu + area σ² + area² σ² / nsky). A manifest beside the table names the IRAF version,
the date, this command and a digest of the input frames.
"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import warnings
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve()
TABLE = HERE.parents[2] / "data" / "hatp32_iraf_phot.csv"
DATA = Path(os.environ.get("ASTROWB_VALIDATION_DATA", "")) / "HatP32Dec202017"
PHOT = (
    "interactive- verify- verbose- datapars.epadu=1 datapars.readnoise=0 centerpars.calgorithm=none "
    "fitskypars.salgorithm=median fitskypars.annulus=10 fitskypars.dannulus=6 fitskypars.slorejec=3 "
    "fitskypars.shirejec=3 fitskypars.snreject=10 photpars.apertures=4 photpars.zmag=25"
)


def centres(frames):
    from astrowb.photometry.lightcurve import light_curve

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        lc = light_curve(frames, (424, 286), [(465, 183), (512, 263)], 4.0, 10.0, 16.0)
    return np.asarray(lc["xy"])  # frames × stars × (x, y), from 0


def iraf(frames, xy, work):
    """phot on every frame at the given centres; rows (file, star, x, y, flux, sky, std, nsky, area)."""
    script = ["noao", "digiphot", "apphot"]
    for i, f in enumerate(frames):
        (work / f"{i}.coo").write_text("".join(f"{x + 1:.3f} {y + 1:.3f}\n" for x, y in xy[i]))
        (work / f"{i}.fits").symlink_to(Path(f).resolve())  # IRAF opens ".fits", not these frames' ".FITS"
        script.append(f"phot {i}.fits coords={i}.coo output={i}.mag {PHOT}")
        script.append(f"txdump {i}.mag XCENTER,YCENTER,FLUX,MSKY,STDEV,NSKY,AREA yes > {i}.txt")
    script.append("logout")
    env = os.environ | {"USER": os.environ.get("USER", "astro"), "HOME": str(work)}  # irafcl wants both
    subprocess.run(["irafcl"], input="\n".join(script) + "\n", text=True, cwd=work, env=env, check=True,
                   capture_output=True)  # fmt: skip
    rows = []
    for i, f in enumerate(frames):
        for star, line in enumerate((work / f"{i}.txt").read_text().split("\n")[: len(xy[i])]):
            x, y, flux, sky, std, nsky, area = (float(v) for v in line.split())
            rows.append((Path(f).name, star, x - 1, y - 1, flux, sky, std, int(nsky), area))
    return rows


def flux_err(flux, std, nsky, area):
    return float(np.sqrt(flux + area * std**2 + area**2 * std**2 / nsky))


def write(rows, frames, out=TABLE):
    lines = ["file,star,x,y,flux,sky,sky_std,nsky,area,flux_err"]
    for f, star, x, y, flux, sky, std, nsky, area in rows:
        err = flux_err(flux, std, nsky, area)
        lines.append(f"{f},{star},{x:.3f},{y:.3f},{flux:.4f},{sky:.4f},{std:.4f},{nsky},{area:.4f},{err:.4f}")
    out.write_text("\n".join(lines) + "\n")
    digest = hashlib.sha256()
    for f in frames:
        digest.update(Path(f).read_bytes())
    version = subprocess.run(["dpkg-query", "-W", "-f=${Version}", "iraf"], capture_output=True, text=True).stdout
    manifest = {
        "program": "IRAF apphot.phot",
        "version": version or "unknown",
        "date": time.strftime("%Y-%m-%d"),
        "command": f"python {HERE.relative_to(HERE.parents[4]).as_posix()}",
        "inputs": f"{len(frames)} frames of HatP32Dec202017 (github.com/rzellem/EXOTIC_sampledata)",
        "inputs_sha256": digest.hexdigest(),
    }
    out.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")


def main():
    frames = [str(p) for p in sorted(DATA.glob("*.FITS"))]
    if not frames:
        sys.exit("set ASTROWB_VALIDATION_DATA to the folder that holds HatP32Dec202017")
    with tempfile.TemporaryDirectory() as tmp:
        rows = iraf(frames, centres(frames), Path(tmp))
    write(rows, frames)
    print(TABLE)


if __name__ == "__main__":
    main()
