"""PHO-24: the Images window's Pairs tab — Add to table, Delete, CSV / ECSV export."""

import sys
from pathlib import Path

import numpy as np
from astropy.table import Table

from astrowb.ui.image_page import ImagePage

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_pair_measure import pair_image  # noqa: E402


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


def test_send_to_astrometry_appends_the_pairs_and_opens_the_window(qapp):
    """PHO-24: the Images window's pairs go to the Astrometry window's pairs table, which opens."""
    from types import SimpleNamespace

    from astrowb.ui.image_pair_table import PairTable

    img, w, (x1, y1), (x2, y2), _ = pair_image()
    opened, target = [], PairTable()
    target.pairs = [{"separation_px": 1.0}]
    main = SimpleNamespace(astrometry_page=SimpleNamespace(pair_table=target), open_area=opened.append)
    page = ImagePage()
    page.owner = main
    page.viewer.data, page.wcs = img, w
    page.measure_line(x1 + 1, y1, x2, y2 - 1)
    pairs = page.pair_table
    pairs.send_button.click()  # nothing added yet: nothing sent
    assert opened == [] and len(target.pairs) == 1
    pairs.add_button.click()
    pairs.send_button.click()
    assert opened == ["astrometry"] and len(target.pairs) == 2
    assert target.pairs[1]["dmag"] == pairs.pairs[0]["dmag"] and len(target.table.model.table) == 2
