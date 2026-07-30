import os

import numpy as np
import pytest
from astropy.io import fits

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    monkeypatch.setenv("ASTROWB_CONFIG_DIR", str(tmp_path / "config"))


@pytest.fixture
def fits_file(tmp_path):
    rng = np.random.default_rng(1)
    data = rng.normal(1000, 10, (64, 80)).astype(np.float32)
    data[30:34, 40:44] += 5000  # a "star"
    hdr = fits.Header({"OBJECT": "TEST", "EXPTIME": 30.0})
    path = tmp_path / "frame.fits"
    fits.PrimaryHDU(data, hdr).writeto(path)
    return path
