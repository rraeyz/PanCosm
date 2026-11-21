"""PHO-24: the Images window's Pairs tab — Add to table, Delete, CSV / ECSV export."""

import numpy as np
from astropy.table import Table

from astrowb.ui.image_page import ImagePage
from tests.test_pair_measure import pair_image


def test_add_to_table_twice_and_export(qapp, tmp_path):
    img, w, (x1, y1), (x2, y2), _ = pair_image()
    page = ImagePage()
    page.viewer.data, page.wcs = img, w
    page.measure_line(x1 + 1, y1, x2, y2 - 1)
    pairs = page.pair_table
    pairs.add_button.click()
    page.measure_line(x1, y1 + 0.5, x2 - 1, y2)
    pairs.add_button.click()
    assert len(pairs.table.model.table) == 2
    for name in ("pairs.csv", "pairs.ecsv"):
        pairs.table.export(str(tmp_path / name))
    csv = Table.read(tmp_path / "pairs.csv")
    ecsv = Table.read(tmp_path / "pairs.ecsv")
    assert len(csv) == len(ecsv) == 2
    assert str(ecsv["dmag"].unit) == "mag" and str(ecsv["separation_arcsec"].unit) == "arcsec"
    for n in pairs.table.model.table.colnames:
        assert np.allclose(csv[n], ecsv[n]) and np.allclose(ecsv[n], pairs.table.model.table[n])
    pairs.delete([0])
    assert len(pairs.table.model.table) == 1
