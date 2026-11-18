"""O−C Load of a light-curve file (.lc.ecsv, PHO-48): its eclipses timed at the window's reference ephemeris."""

from pathlib import Path

import numpy as np
from PySide6.QtCore import QCoreApplication

translate = QCoreApplication.translate


def load_lcfile(page, path):
    """Time every minimum of the file's target series with the Photometry step's default timer (Kwee-van
    Woerden, the larger of its two errors) and add them to the page; say why when nothing is added."""
    from ..photometry import lcfile
    from ..timeseries.minima import each_minimum, kwee_van_woerden

    name = Path(path).name
    try:
        t0, period = float(page.t0.text()), float(page.period.text())
        t, y, _, _ = lcfile.series(path)
    except ValueError as e:  # empty ephemeris fields, or a file that is not a light-curve file
        msg = translate("OCPage", "{file}: type the reference T0 and period first, to time its minima.")
        page.result.setText(msg.format(file=name) if "float" in str(e) else translate(e))
        return

    def timer(tw, yw):
        tm, s_kvw, s_boot = kwee_van_woerden(tw, yw)
        return tm, float(np.nanmax([s_kvw, s_boot]))

    found, _ = each_minimum(t, y / np.median(y), t0, period, timer)
    if not found:
        page.result.setText(
            translate("OCPage", "{file}: no whole minimum at the times of this ephemeris.").format(file=name)
        )
        return
    for tm, err, kind in found:
        page.add_minimum(tm, err, name, kind)
    page.result.setText(translate("OCPage", "{n} minima timed in {file}.").format(n=len(found), file=name))
