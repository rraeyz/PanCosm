"""The Light curves page: the period, frequency and variable-search tabs together (O-C has its own window)."""

from PySide6.QtWidgets import (
    QTabWidget,
)

from .period_page import PeriodPage


class LightCurvePage(QTabWidget):
    """Light curves: period search, frequency analysis and variable star search as tabs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.period_page = PeriodPage(self)
        from .frequency_page import FrequencyPage
        from .varfind_page import VarFindPage

        self.frequency_page = FrequencyPage(self.period_page, self)
        self.varfind_page = VarFindPage(self)
        self.addTab(self.period_page, self.tr("Period search"))
        self.addTab(self.frequency_page, self.tr("Frequency analysis"))
        self.addTab(self.varfind_page, self.tr("Variable star search"))
