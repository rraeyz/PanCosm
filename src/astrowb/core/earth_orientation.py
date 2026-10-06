"""Earth-orientation (IERS-A) and leap-second tables: never a reason for the program to stop (plans/architecture.md
ARC-1).

Astropy needs UT1 - UTC and polar motion for every altitude / azimuth (airmass, planning, telescope safety). It
reads them from a table shipped with the installation. Left at its defaults it then *raises an error* for times
after the table's measured part once the table is more than 30 days old (`iers.conf.auto_max_age`), so an
installation a month old stopped computing altitudes. Predictions a year ahead are good to ~0.1 s in UT1
(1.5 arcsec in hour angle): far below what airmass or a pointing limit needs. BJD_TDB does not use UT1 at all.

configure() is idempotent and cheap (no file is read): every module that computes alt-az imports this module.
refresh() downloads newer tables (on request, or weekly when the user allows it) into the user's folder; the
newest one is used from then on, in this process and every worker.
"""

import datetime as _dt
import json
import os
import re
from pathlib import Path

REFRESH_DAYS = 7
_configured = False


def folder() -> Path:
    from ..settings import config_dir

    return config_dir() / "earth-orientation"


def _bundled_date() -> _dt.date | None:
    """Date of the tables shipped with the installation (from astropy-iers-data's version 0.YYYY.MM.DD...)."""
    try:
        import astropy_iers_data

        y, m, d = re.match(r"0\.(\d{4})\.(\d{1,2})\.(\d{1,2})", astropy_iers_data.__version__).groups()
        return _dt.date(int(y), int(m), int(d))
    except Exception:  # unknown packaging: treat the stored copy as newer
        return None


def _stored() -> dict:
    try:
        return json.loads((folder() / "state.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def configure() -> None:
    """Never download on our own, never refuse an old table (warn instead), and use the newest stored table."""
    global _configured
    if _configured:
        return
    _configured = True
    from astropy.utils import iers

    iers.conf.auto_download = False
    iers.conf.auto_max_age = None  # the 30-day refusal: off (see the module docstring)
    iers.conf.iers_degraded_accuracy = "warn"
    use_stored()


def use_stored() -> None:
    """Use the tables refresh() stored, when they are newer than the bundled ones."""
    from astropy.utils import iers

    state = _stored()
    bundled = _bundled_date()
    try:
        downloaded = _dt.date.fromisoformat(state["date"])
    except (KeyError, ValueError):
        return
    if bundled is not None and downloaded <= bundled:
        return
    table, leap = folder() / "finals2000A.all", folder() / "Leap_Second.dat"
    try:
        if table.exists():
            iers.earth_orientation_table.set(iers.IERS_Auto.read(str(table)))
        if leap.exists():
            iers.conf.system_leap_second_file = str(leap)
    except Exception:  # a damaged copy: set it aside and keep the bundled tables (time.table_unreadable)
        for f in (table, leap, folder() / "state.json"):
            try:
                f.replace(f.with_suffix(f.suffix + ".bad"))
            except OSError:
                pass


def status() -> dict:
    """{source, table_date, age_days, covers_until, measured_until} of the table in use (reads it: ~1 s)."""
    configure()
    from astropy.time import Time
    from astropy.utils import iers

    t = iers.earth_orientation_table.get()
    now = Time.now().mjd
    predictive = t.meta.get("predictive_mjd")
    measured = float(predictive) if predictive is not None else float(t["MJD"][-1].value)
    stored = _stored()
    return {
        "source": "downloaded"
        if stored and _dt.date.fromisoformat(stored["date"]) > (_bundled_date() or _dt.date.min)
        else "bundled",
        "table_date": Time(measured, format="mjd").iso[:10],
        "age_days": float(now - measured),
        "covers_until": Time(float(t["MJD"][-1].value), format="mjd").iso[:10],
    }


def due(today: _dt.date | None = None) -> bool:
    """True when the stored (or bundled) tables are older than REFRESH_DAYS."""
    today = today or _dt.date.today()
    try:
        last = _dt.date.fromisoformat(_stored()["date"])
    except (KeyError, ValueError):
        last = _bundled_date() or _dt.date.min
    return (today - last).days >= REFRESH_DAYS


def _fetch(url: str, timeout: float) -> bytes:
    import ssl
    import urllib.request

    import certifi

    ctx = ssl.create_default_context(cafile=certifi.where())
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:  # noqa: S310 (fixed https URLs)
        return r.read()


def refresh(fetch=None, timeout: float = 20.0) -> dict:
    """Download the IERS-A table and the leap-second list, check that they parse, store them atomically and use
    them. fetch(url, timeout) -> bytes (for tests). Raises OSError / ValueError when nothing usable came; the old
    tables then stay in use."""
    import astropy_iers_data as data
    from astropy.utils import iers

    fetch = fetch or _fetch
    folder().mkdir(parents=True, exist_ok=True)

    def first(urls):
        errors = []
        for url in urls:
            try:
                return fetch(url, timeout)
            except Exception as e:  # try the mirror
                errors.append(f"{url}: {e}")
        raise OSError("; ".join(errors))

    table = folder() / "finals2000A.all"
    tmp = table.with_suffix(".tmp")
    tmp.write_bytes(first([data.IERS_A_URL, data.IERS_A_URL_MIRROR]))
    parsed = iers.IERS_Auto.read(str(tmp))  # raises if this is not an IERS-A table
    if len(parsed) < 1000:
        tmp.unlink()
        raise ValueError("the downloaded Earth-orientation table is too short: the server did not send the whole file")
    os.replace(tmp, table)
    leap = folder() / "Leap_Second.dat"
    try:
        content = first([data.IERS_LEAP_SECOND_URL, data.IERS_LEAP_SECOND_URL_MIRROR])
        ltmp = leap.with_suffix(".tmp")
        ltmp.write_bytes(content)
        iers.LeapSeconds.from_iers_leap_seconds(str(ltmp))  # raises if it does not parse
        os.replace(ltmp, leap)
        iers.conf.system_leap_second_file = str(leap)
    except Exception:  # leap seconds change rarely: the bundled list is kept
        pass
    (folder() / "state.json").write_text(json.dumps({"date": _dt.date.today().isoformat()}), encoding="utf-8")
    iers.earth_orientation_table.set(parsed)
    return status()


def describe(st: dict) -> str:
    """One line for reports: "downloaded table of 2026-11-09 (3 days old; predictions to 2027-11-15)"."""
    return (
        f"{st['source']} table of {st['table_date']} ({st['age_days']:.0f} days old; "
        f"predictions to {st['covers_until']})"
    )
