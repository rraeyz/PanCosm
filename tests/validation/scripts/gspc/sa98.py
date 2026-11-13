"""Fetch the Gaia DR3 GSPC magnitudes of Landolt's Selected Area 98 (plans/photometry.md PHO-25 item 6) from the ESA
Gaia archive: every GSPC star in the field's box, written as tests/validation/data/photometry/gspc_sa98.csv with its
manifest. The test matches them to Landolt (1992) within 2 arcsec.

    python tests/validation/scripts/gspc/sa98.py
"""

import hashlib
import json
from pathlib import Path

from astroquery.gaia import Gaia

OUT = Path(__file__).resolve().parents[2] / "data" / "photometry"
QUERY = ("SELECT g.source_id, g.ra, g.dec, g.phot_g_mean_mag, s.b_jkc_mag, s.b_jkc_flag, s.v_jkc_mag, s.v_jkc_flag, "
         "s.r_jkc_mag, s.r_jkc_flag, s.i_jkc_mag, s.i_jkc_flag FROM gaiadr3.gaia_source AS g "
         "JOIN gaiadr3.synthetic_photometry_gspc AS s ON s.source_id = g.source_id "
         "WHERE g.ra BETWEEN 102.80 AND 103.23 AND g.dec BETWEEN -0.52 AND -0.12")  # fmt: skip


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    t = Gaia.launch_job(QUERY).get_results()
    path = OUT / "gspc_sa98.csv"
    t.write(path, format="ascii.csv", overwrite=True)
    manifest = {"program": "ESA Gaia archive (gaiadr3.synthetic_photometry_gspc)", "date": "2026-11-14",
                "command": "python tests/validation/scripts/gspc/sa98.py", "inputs": QUERY,
                "output_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}  # fmt: skip
    (OUT / "gspc_sa98.manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
