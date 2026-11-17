"""PHO-18: the Measure stage's banner when catalogue stars lie in a measured star's sky ring."""

from PySide6.QtCore import QCoreApplication

from ..photometry.neighbours import find
from .kit.banners import InfoBanner

translate = QCoreApplication.translate
MATCH = 3.0  # px: a Gaia star this close to the marked target is the target


def neighbour_banner(page):
    """Show (or clear) page.neighbour_banner after a measurement. The target's magnitude is that of the Gaia star
    on it; no Gaia stars or no match on the target: no banner (nothing is guessed)."""
    old = getattr(page, "neighbour_banner", None)
    if old is not None:
        old.hide()
        old.deleteLater()
        page.neighbour_banner = None
    stars = (page.field or {}).get("stars") if page.field else None
    if not stars or page.target is None or page.remove_neighbours.isChecked():
        return None
    tx, ty = page.target
    d, k = min(
        (((x - tx) ** 2 + (y - ty) ** 2) ** 0.5, k) for k, (x, y) in enumerate(zip(stars["x"], stars["y"], strict=True))
    )
    if d > MATCH:
        return None
    pts = [tuple(page.target)] + [tuple(c) for c in page.comps]
    names = ["T1"] + [f"C{i}" for i in range(1, len(page.comps) + 1)]
    found = find(pts, stars, page.r_out.value(), stars["gmag"][k])
    if not found:
        return None
    n = len({(h["x"], h["y"]) for f in found for h in f["neighbours"]})
    text = translate(
        "PhotometryBanner",
        "{n} catalogue star(s) brighter than the target + 4 mag lie inside the sky ring of {stars}. "
        "Measuring with “Remove neighbours” may give a cleaner light curve.",
    ).format(n=n, stars=", ".join(names[f["index"]] for f in found))
    on = translate("PhotometryBanner", "Turn on “Remove neighbours”")
    banner = InfoBanner("attention", text, [(on, lambda: page.remove_neighbours.setChecked(True))], page)
    body = page.sections[3].body
    body.insertWidget(body.indexOf(page.measure_button), banner)
    page.neighbour_banner = banner
    return banner
