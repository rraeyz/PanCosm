"""PHO-25 item 6: the Gaia DR3 GSPC V magnitudes (the first source of the comparison stars' V) against Landolt's
standards in Selected Area 98 (Landolt 1992, the bundled list; GSPC from a recorded archive answer, made again by
scripts/gspc/sa98.py). Landolt's positions are rounded to 1 s of RA (15″): a GSPC star within 12″ is taken when its V
is within 0.5 mag, the nearest in V. The GSPC paper states < 0.02 mag mean and < 0.03 scatter against Landolt."""

from pathlib import Path

import numpy as np
import pytest
from astropy.table import Table

from astrowb.planning.standards import load

DATA = Path(__file__).parent / "data" / "photometry" / "gspc_sa98.csv"
pytestmark = pytest.mark.validation


def test_gspc_v_against_landolt_sa98(measured):
    landolt = load("landolt1992")
    landolt = landolt[[n.startswith("98 ") for n in landolt["name"]]]
    gspc = Table.read(DATA, format="ascii.csv")
    gspc = gspc[np.asarray(gspc["v_jkc_flag"]) == 1]
    diff = []
    for star in landolt:
        sep = 3600 * np.hypot((gspc["ra"] - star["ra"]) * np.cos(np.radians(star["dec"])), gspc["dec"] - star["dec"])
        near = np.flatnonzero(sep < 12)
        if len(near):
            k = near[np.argmin(np.abs(gspc["v_jkc_mag"][near] - star["V"]))]
            if abs(gspc["v_jkc_mag"][k] - star["V"]) < 0.5:
                diff.append(float(gspc["v_jkc_mag"][k] - star["V"]))
    diff = np.array(diff)
    mean, scatter = float(np.mean(diff)), float(np.std(diff))
    measured("photometry", f"GSPC V − Landolt V, SA 98 ({len(diff)} stars), mean (mag)", "Landolt (1992)", "0.02",
             mean, abs(mean) < 0.02, data=DATA.name, step="photometry.catalog")  # fmt: skip
    measured("photometry", "GSPC V − Landolt V, SA 98, scatter (mag)", "Landolt (1992)", "0.03", scatter,
             scatter < 0.03, data=DATA.name, step="photometry.catalog")  # fmt: skip
    assert len(diff) >= 10 and abs(mean) < 0.02 and scatter < 0.03
