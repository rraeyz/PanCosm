"""File-dialog filters shared by the pages."""

from PySide6.QtCore import QCoreApplication

from ..io.bayer import OPEN_PATTERNS


def images_filter():
    """Every kind of image the application opens: FITS, camera raw files and ordinary pictures (converted)."""
    label = QCoreApplication.translate("Files", "Images: FITS, camera raw, JPEG, PNG, TIFF")
    return f"{label} ({OPEN_PATTERNS});;FITS (*.fits *.fit *.fts *.fits.gz *.fits.fz)"
