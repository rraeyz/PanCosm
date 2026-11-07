"""The Light curves page: the period, frequency, variable-search and O-C tabs together."""

from PySide6.QtWidgets import (
    QTabWidget,
)

from .oc_page import OCPage
from .period_page import PeriodPage


class LightCurvePage(QTabWidget):
    """Light curves & O-C: period search and O-C diagram as tabs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.period_page = PeriodPage(self)
        self.oc_page = OCPage(self)
        from .frequency_page import FrequencyPage
        from .varfind_page import VarFindPage

        self.frequency_page = FrequencyPage(self.period_page, self)
        self.varfind_page = VarFindPage(self)
        self.addTab(self.period_page, self.tr("Period search"))
        self.addTab(self.frequency_page, self.tr("Frequency analysis"))
        self.addTab(self.varfind_page, self.tr("Variable star search"))
        self.addTab(self.oc_page, self.tr("O-C diagram"))
