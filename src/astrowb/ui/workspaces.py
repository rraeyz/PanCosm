"""Workspaces: the pages of the main window, one module each (re-exported here so that older imports keep working)."""

from PySide6.QtWidgets import QFileDialog  # noqa: F401  (tests patch it through this module)

from .calibrate_page import CalibratePage, by_filter  # noqa: F401
from .image_page import ImagePage  # noqa: F401
from .lightcurve_page import LightCurvePage  # noqa: F401
from .oc_page import OCPage, _decimals  # noqa: F401
from .period_page import PeriodPage, fold_phase, fourier_edit  # noqa: F401
from .photometry_page import AavsoDialog, PhotometryPage, _without_frames, export_csv  # noqa: F401
from .project_page import ProjectPage  # noqa: F401
from .start_page import StartPage  # noqa: F401
from .widgets import Collapsible, PlotCanvas, StepGuide, _canvas_class, _FoldButton, _title  # noqa: F401
