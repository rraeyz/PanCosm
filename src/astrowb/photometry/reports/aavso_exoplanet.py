"""The AAVSO Exoplanet Database file (plans/photometry.md PHO-27, the rules written under that step): header lines
`#KEY=value` (case sensitive, `#TYPE=EXOPLANET` first and mandatory), then data rows: date, the differential
measurement named by `#MEASUREMENT_TYPE`, its error, and `DETREND_1` … `DETREND_4` only when the header names
them. A blank line not commented with `#` makes WebObs reject the file, so none is written.

shortcut: the MEASUREMENT_TYPE codes (Rnflux for normalised relative flux, Dmag for differential magnitude) follow
EXOTIC's output; check them against the AAVSO users guide when a browser can open it.
"""

import numpy as np

KEYS = ("TYPE", "OBSCODE", "SOFTWARE", "DELIM", "DATE_TYPE", "OBSTYPE", "STAR_NAME", "EXOPLANET_NAME", "BINNING",
        "EXPOSURE_TIME", "FILTER", "DETREND_PARAMETERS", "MEASUREMENT_TYPE", "PRIORS")  # fmt: skip


def write(path, time, value, error, header, detrend=None):
    """header: the values of KEYS (TYPE, DELIM and DATE_TYPE are set here); detrend: {name: series}, at most four."""
    detrend = dict(detrend or {})
    if len(detrend) > 4:
        raise ValueError("the AAVSO exoplanet file takes at most four detrending columns")
    h = {"TYPE": "EXOPLANET", "DELIM": ",", "DATE_TYPE": "BJD_TDB"} | {k: v for k, v in header.items() if v}
    if detrend:
        h["DETREND_PARAMETERS"] = ",".join(detrend)
    lines = [f"#{k}={h[k]}" for k in KEYS if k in h]
    cols = [np.asarray(time, float), np.asarray(value, float), np.asarray(error, float)]
    cols += [np.asarray(v, float) for v in detrend.values()]
    for row in zip(*cols, strict=True):
        lines.append(",".join(f"{x:.7f}" if i == 0 else f"{x:.6f}" for i, x in enumerate(row)))
    text = "\n".join(lines) + "\n"
    problems = validate(text)
    if problems:
        raise ValueError(problems[0])
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return path


def validate(text):
    """The format's rules, re-read from the file: a list of problems (empty when it would be accepted)."""
    lines = text.splitlines()
    out = []
    if not lines or lines[0] != "#TYPE=EXOPLANET":
        out.append("the first line must be #TYPE=EXOPLANET")
    header = {}
    for n, line in enumerate(lines, 1):
        if not line.strip():
            out.append(f"line {n} is blank: WebObs rejects a blank line not commented with #")
        elif line.startswith("#"):
            key, _, value = line[1:].partition("=")
            if key not in KEYS:
                out.append(f"line {n}: unknown header key {key}")
            header[key] = value
    n_detrend = len(header.get("DETREND_PARAMETERS", "").split(",")) if header.get("DETREND_PARAMETERS") else 0
    expected = 3 + n_detrend
    for n, line in enumerate(lines, 1):
        if line.strip() and not line.startswith("#") and len(line.split(",")) != expected:
            out.append(f"line {n}: {expected} columns expected")
            break
    for key in ("OBSCODE", "STAR_NAME", "FILTER", "MEASUREMENT_TYPE"):
        if not header.get(key):
            out.append(f"the header needs #{key}")
    return out
