"""Lines of the Photometry result summary that say which frames became points (UF-18)."""

from PySide6.QtCore import QCoreApplication

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("Ctx", "…") calls


def frames_lines(page, n_points):
    """Where the frames of the list went: how many became points, and how many were measured against fewer
    comparison stars than the others."""
    lines = []
    listed = getattr(page, "_measured_frames", n_points)
    if listed != n_points:
        text = translate(
            "PhotometryPage", "{n} of the {m} frames in the list became points; the others are named below."
        )
        lines.append(text.format(n=n_points, m=listed))
    partial = (page.lc_raw or {}).get("partial") or {}
    if partial:
        text = translate(
            "PhotometryPage",
            "{n} frame(s) without some comparison stars, kept against the others (orange in the frame list).",
        )
        lines.append(text.format(n=len(partial)))
    return lines
