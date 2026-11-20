"""The Photometry window's Images stage summary (plans/interface.md UI-16.1): how many frames, over what time, which
filters, whether the headers say they are calibrated, and the bad frames with their reasons. Built from what the page
already holds (frame times, the quality rows); only the filter and calibration keywords are read from the headers."""

from pathlib import Path

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QLabel

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("PhotometryImages", "…") calls
CALIBRATION = {"CALB": "bias", "CALD": "dark", "CALF": "flat"}  # what calibration/steps.py writes into each light
SAMPLE = 40  # shortcut: the headers of 40 frames spread over the night stand for all, a longer read is slow


def header_facts(paths):
    """(filters, calibration kinds) from the headers of up to SAMPLE frames spread over the list."""
    from astropy.io import fits

    step = max(1, len(paths) // SAMPLE)
    filters, done = set(), set()
    for p in paths[::step]:
        try:
            header = fits.getheader(p)
        except (OSError, ValueError):
            continue
        name = next((header[k] for k in ("FILTER", "FILTNAM", "FILT") if header.get(k)), None)
        if name:
            filters.add(str(name).strip())
        done |= {kind for key, kind in CALIBRATION.items() if str(header.get(key, "none")).lower() not in ("none", "")}
    return sorted(filters), sorted(done)


def span_text(jds):
    if len(jds) < 2:
        return ""
    hours = (max(jds) - min(jds)) * 24
    return translate("PhotometryImages", "over {h:.1f} h").format(h=hours)


def summary(page, facts):
    from .messages import translate as message

    filters, done = facts
    n = len(page.images)
    span = span_text(list(getattr(page, "_frame_jd", {}).values()))
    lines = [translate("PhotometryImages", "{n} frames {span}").format(n=n, span=span).strip()]
    lines.append(
        translate("PhotometryImages", "Filters: {f}").format(f=", ".join(filters))
        if filters
        else translate("PhotometryImages", "Filters: none named in the headers")
    )
    lines.append(
        translate("PhotometryImages", "Calibrated: yes ({kinds})").format(kinds=", ".join(done))
        if done
        else translate("PhotometryImages", "Calibrated: the headers do not say (raw frames?)")
    )
    rows = getattr(page, "quality", None) or []
    bad = [r for r in rows if not r["good"]]
    if not rows:
        lines.append(translate("PhotometryImages", "Bad frames: not checked yet (Find the bad frames)"))
    elif not bad:
        lines.append(translate("PhotometryImages", "Bad frames: none"))
    else:
        lines.append(translate("PhotometryImages", "Bad frames: {k}").format(k=len(bad)))
        lines += [f"  {Path(r['file']).name}: {', '.join(message(w) for w in r['why'])}" for r in bad[:6]]
        if len(bad) > 6:
            lines.append(translate("PhotometryImages", "  and {k} more").format(k=len(bad) - 6))
    return "\n".join(lines)


def attach(win, page):
    """The summary under the Images stage; it follows the frame list, which the page refills whenever the frames or
    their quality change."""
    label = QLabel(win.stage_panels["images"])
    label.setObjectName("images_summary")
    label.setWordWrap(True)
    label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    win.stage_panels["images"].add(label)
    seen = {}
    fill = page._fill_frames

    def refill():
        fill()
        key = tuple(page.images)
        if seen.get("key") != key:
            seen["key"], seen["facts"] = key, header_facts(list(key)) if key else ([], [])
        label.setVisible(bool(key))
        if key:
            label.setText(summary(page, seen["facts"]))

    page._fill_frames = refill
