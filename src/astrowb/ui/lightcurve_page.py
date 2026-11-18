"""The Light curves page: the period, frequency and variable-search tabs together (O-C has its own window)."""

from PySide6.QtWidgets import (
    QTabWidget,
)

from .occultation_tab import OccultationTab
from .period_page import PeriodPage


class LightCurvePage(QTabWidget):
    """Light curves: period search, frequency analysis, variable star search and occultation timing as tabs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.period_page = PeriodPage(self)
        from . import varfind_export
        from .frequency_page import FrequencyPage
        from .varfind_page import VarFindPage

        self.frequency_page = FrequencyPage(self.period_page, self)
        self.varfind_page = VarFindPage(self)
        varfind_export.attach(self.varfind_page)
        self.addTab(self.period_page, self.tr("Period search"))
        self.addTab(self.frequency_page, self.tr("Frequency analysis"))
        self.addTab(self.varfind_page, self.tr("Variable star search"))
        self.occultation_tab = OccultationTab(self)
        self.addTab(self.occultation_tab, self.tr("Occultation"))
