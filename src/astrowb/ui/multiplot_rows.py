"""Each multi-plot row's own detrending (plans/photometry.md PHO-46, AstroImageJ's Y-data rows): right-click a series
in the list → none, as the target, or its own set of quantities; kept in the plot template."""

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QMenu

from ..photometry.differential import covariates
from ..photometry.multiplot import QUANTITIES, detrend_row

DETREND = Qt.UserRole + 1
translate = QCoreApplication.translate  # pyside6-lupdate reads translate("Ctx", "…") calls


def multi_rows(listw):
    """The ticked rows: {key, colour, detrend}."""
    items = [listw.item(i) for i in range(listw.count())]
    return [{"key": it.text(), "colour": it.data(Qt.UserRole), "detrend": it.data(DETREND)}
            for it in items if it.checkState() == Qt.Checked]  # fmt: skip


def restore_detrend(listw, rows):
    for r in rows:
        for it in listw.findItems(r["key"], Qt.MatchExactly):
            _set(it, r.get("detrend"))


def _set(item, choice):
    item.setData(DETREND, choice or None)
    if choice == "target":
        text = translate("MultiplotRows", "detrended as the target")
    elif choice:
        text = translate("MultiplotRows", "detrended against {names}").format(names=", ".join(choice))
    else:
        text = translate("MultiplotRows", "not detrended")
    item.setToolTip(text + " — " + translate("MultiplotRows", "right-click to change"))


def with_detrend_menu(page):
    page.multi_series.setContextMenuPolicy(Qt.CustomContextMenu)
    page.multi_series.customContextMenuRequested.connect(lambda pos: detrend_menu(page, pos).exec(
        page.multi_series.viewport().mapToGlobal(pos)))  # fmt: skip


def detrend_menu(page, pos):
    """The menu for the series under pos: none, as the target, or a ticked set of the light curve's quantities."""
    menu = QMenu(page)
    item = page.multi_series.itemAt(pos)
    if item is None or item.text() in QUANTITIES or page.lc_raw is None:
        return menu
    now = item.data(DETREND)

    def choose(choice):
        _set(item, choice)
        page._plot_current()

    menu.addAction(translate("MultiplotRows", "No detrending")).triggered.connect(lambda: choose(None))
    menu.addAction(translate("MultiplotRows", "Detrend as the target")).triggered.connect(lambda: choose("target"))
    menu.addSeparator()
    own = list(now) if isinstance(now, list) else []
    for name in [k for k in covariates(page.lc_raw) if k != "time"] + ["time"]:
        a = menu.addAction(name)
        a.setCheckable(True)
        a.setChecked(name in own)
        a.triggered.connect(lambda on, n=name: choose(sorted(set(own) | {n}) if on else [k for k in own if k != n]))
    return menu


def detrended(page, lc, row, y):
    """The row's values divided by its own trend; unchanged when it has none or the fit cannot be made."""
    if row["key"] in QUANTITIES or not row.get("detrend"):
        return y
    target_set = page.detrend_cfg[0] if page.detrend_cfg else ()
    try:
        return detrend_row(lc, y, row["detrend"], target_set, page._left_out_range())
    except ValueError:
        return y
