"""PHO-27: the AAVSO exoplanet file passes its own format check; broken files are caught."""

import numpy as np
import pytest

from astrowb.photometry.reports import aavso_exoplanet as ax

HEADER = {"OBSCODE": "XYZ", "SOFTWARE": "test", "OBSTYPE": "CCD", "STAR_NAME": "Qatar-1",
          "EXOPLANET_NAME": "Qatar-1 b", "BINNING": "1x1", "EXPOSURE_TIME": "60", "FILTER": "R",
          "MEASUREMENT_TYPE": "Rnflux", "PRIORS": "none"}  # fmt: skip


def test_write_and_validate(tmp_path):
    t = 2459800.5 + np.arange(5) / 1440
    p = ax.write(tmp_path / "q.txt", t, np.ones(5), np.full(5, 0.002), HEADER, {"AIRMASS": np.linspace(1.1, 1.3, 5)})
    text = p.read_text()
    lines = text.splitlines()
    assert lines[0] == "#TYPE=EXOPLANET" and "#DETREND_PARAMETERS=AIRMASS" in lines and "#DATE_TYPE=BJD_TDB" in lines
    assert lines[-1].count(",") == 3 and not ax.validate(text)
    assert any("blank" in m for m in ax.validate(text.replace("#FILTER=R", "")))
    assert any("columns" in m for m in ax.validate(text + "1,2\n"))
    assert any("needs #OBSCODE" in m for m in ax.validate(text.replace("#OBSCODE=XYZ\n", "")))
    with pytest.raises(ValueError):
        ax.write(tmp_path / "x.txt", t, np.ones(5), np.ones(5), HEADER, {f"D{i}": np.ones(5) for i in range(5)})
