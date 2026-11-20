"""AAVSO Extended File Format writer (PHO-27 item 2; transformed with PHO-35's coefficients), moved here from
photometry/export.py. Columns (in this order): NAME, DATE, MAG, MERR, FILT, TRANS, MTYPE, CNAME, CMAG, KNAME, KMAG,
AIRMASS, GROUP, CHART, NOTES; header lines #TYPE, #OBSCODE, #SOFTWARE, #DELIM, #DATE, #OBSTYPE; unused optional
fields are "na". DATE is the mid-exposure JD (UTC)."""

import numpy as np

from ... import __version__
from ..export import ensemble_magnitudes

COLUMNS = "NAME,DATE,MAG,MERR,FILT,TRANS,MTYPE,CNAME,CMAG,KNAME,KMAG,AIRMASS,GROUP,CHART,NOTES"


def aavso_extended(
    lc,
    star_name,
    obscode,
    filt,
    comp_mags,
    chart="na",
    notes="na",
    software_name="",
    check=None,
    check_name=None,
    transform=None,
) -> str:
    """check: the check star's relative flux per frame (against the same ensemble); its magnitude goes into KMAG
    with check_name (its chart label) in KNAME, as the AAVSO asks for ensemble photometry. transform: {"colour_c"
    (the comparison stars' colours), "colour_t" (the target's, one or per frame), "coefficient", "name" (e.g.
    Tv_bv), optional "error"}: the magnitudes in the standard system (photometry/transform.py), TRANS=YES, and the
    coefficient written in NOTES (PHO-35)."""
    if not star_name or not obscode or not filt:
        raise ValueError("star name, observer code and filter are required")
    if transform:
        from ..transform import transformed

        mag, merr = transformed(lc, comp_mags, transform["colour_c"], transform["colour_t"],
                                transform["coefficient"], transform.get("error", 0.0))  # fmt: skip
        note = f"{transform.get('name', 'T')}={transform['coefficient']:.3f}"
        notes, trans = (note if notes in ("", "na") else f"{notes}|{note}"), "YES"
    else:
        mag, merr = ensemble_magnitudes(lc, comp_mags)
        trans = "NO"
    kmag = ensemble_magnitudes(lc | {"rel_flux": check, "rel_flux_err": check}, comp_mags)[0] if check else None
    airmass = lc.get("airmass") or ["na"] * len(mag)
    lines = [
        "#TYPE=Extended",
        f"#OBSCODE={obscode}",
        f"#SOFTWARE={software_name} {__version__}".strip(),
        "#DELIM=,",
        "#DATE=JD",
        "#OBSTYPE=CCD",
        "#" + COLUMNS,
    ]
    for i, (jd, m, e, am) in enumerate(zip(lc["jd_utc"], mag, merr, airmass, strict=True)):
        if not (np.isfinite(m) and np.isfinite(e) and np.isfinite(jd)):
            continue  # a lost star, a bad frame or a frame without its time is not reported
        am_text = f"{am:.4f}" if isinstance(am, float) else "na"
        k = f"{check_name or 'check'},{kmag[i]:.3f}" if kmag is not None and np.isfinite(kmag[i]) else "na,na"
        lines.append(
            f"{star_name},{jd:.5f},{m:.3f},{e:.3f},{filt},{trans},STD,ENSEMBLE,na,{k},{am_text},na,{chart},{notes}"
        )
    text = "\n".join(lines) + "\n"
    problems = validate(text)
    if problems:
        raise ValueError(problems[0])
    return text


def validate(text):
    """The format's rules, re-read from the file: a list of problems (empty when it would be accepted): #TYPE=Extended
    first, an #OBSCODE, the column line, and data rows of 15 fields whose DATE, MAG and MERR are numbers."""
    lines = text.splitlines()
    out = [] if lines and lines[0] == "#TYPE=Extended" else ["the first line must be #TYPE=Extended"]
    if not any(x.startswith("#OBSCODE=") and len(x) > 9 for x in lines):
        out.append("the header needs #OBSCODE")
    if "#" + COLUMNS not in lines:
        out.append("the header needs the column line")
    for n, line in enumerate(lines, 1):
        if line.startswith("#") or not line.strip():
            continue
        fields = line.split(",")
        if len(fields) != 15:
            out.append(f"line {n}: 15 columns expected")
            continue
        for x in fields[1:4]:
            try:
                float(x)
            except ValueError:
                out.append(f"line {n}: {x} is not a number")
    return out
