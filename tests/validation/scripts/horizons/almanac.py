"""Fetch the planning almanac references (plans/planning.md PLN-14) from JPL Horizons: the Sun's and the Moon's
airless apparent azimuth and elevation, and the Moon's illuminated fraction, every 10 minutes over one day at four
sites. Writes tests/validation/data/planning/horizons_almanac.csv and its manifest.

    python tests/validation/scripts/horizons/almanac.py
"""

import csv
import hashlib
import json
import urllib.parse
import urllib.request
from pathlib import Path

SITES = {  # name: (east longitude deg, latitude deg, height km)
    "Ankara": (32.78, 39.84, 1.25),
    "La Palma": (-17.88, 28.76, 2.33),
    "Siding Spring": (149.07, -31.27, 1.16),
    "Mauna Kea": (-155.47, 19.82, 4.2),
}
START, STOP, STEP = "2026-11-14 00:00", "2026-11-15 00:00", "10 m"
OUT = Path(__file__).resolve().parents[2] / "data" / "planning"


def rows(body, site):
    lon, lat, h = SITES[site]
    q = {"format": "text", "COMMAND": f"'{body}'", "EPHEM_TYPE": "OBSERVER", "CENTER": "'coord@399'",
         "COORD_TYPE": "GEODETIC", "SITE_COORD": f"'{lon},{lat},{h}'", "START_TIME": f"'{START}'",
         "STOP_TIME": f"'{STOP}'", "STEP_SIZE": f"'{STEP}'", "QUANTITIES": "'4,10'", "APPARENT": "AIRLESS",
         "CSV_FORMAT": "YES", "ANG_FORMAT": "DEG"}  # fmt: skip
    text = urllib.request.urlopen("https://ssd.jpl.nasa.gov/api/horizons.api?" + urllib.parse.urlencode(q),
                                  timeout=120).read().decode()  # fmt: skip
    body_rows = text[text.index("$$SOE") + 5 : text.index("$$EOE")].strip().splitlines()
    for line in body_rows:
        f = [c.strip() for c in line.split(",")]
        yield f[0], float(f[3]), float(f[4]), float(f[5])  # date, azimuth, elevation, illuminated %


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "horizons_almanac.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["site", "body", "utc", "az", "alt", "illum"])
        for site in SITES:
            for body, code in (("sun", "10"), ("moon", "301")):
                for date, az, alt, ill in rows(code, site):
                    w.writerow([site, body, date, az, alt, ill])
    manifest = {"program": "JPL Horizons API (observer table, airless apparent)", "date": "2026-11-14",
                "command": "python tests/validation/scripts/horizons/almanac.py",
                "inputs": f"sites {SITES}, {START} to {STOP} every {STEP} UT",
                "output_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}  # fmt: skip
    (OUT / "horizons_almanac.manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
