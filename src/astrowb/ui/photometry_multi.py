"""Multi-plot as a results tab (plans/photometry.md PHO-W): its controls (series, bin, normalise, detrend per row)
leave the Light curve stage for a tab of their own beside Stars, Measurements, Frames and Checks. The drawing is the
page's own `show_what == "multi"` view: the tab only chooses it, and choosing it in the list opens the tab."""

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QFrame, QScrollArea, QVBoxLayout, QWidget

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("PhotometryMulti", "…") calls


def attach(page):
    tabs, what = page.res_tabs, page.show_what
    inner = QWidget()
    lay = QVBoxLayout(inner)
    lay.addWidget(page.multi_box)  # leaves the stage it was in
    lay.addStretch(1)
    box = QScrollArea(page)
    box.setWidgetResizable(True)
    box.setFrameShape(QFrame.NoFrame)
    box.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    box.setWidget(inner)
    tabs.addTab(box, translate("PhotometryMulti", "Multi-plot"))

    def tab_changed(_i):
        if tabs.currentWidget() is not box:
            return
        k = what.findData("multi")
        if k < 0 or not what.isEnabled():  # nothing measured yet: the list has no multi-plot to choose
            page.result.setText(translate("PhotometryMulti", "Measure the light curve first."))
            tabs.setCurrentIndex(0)
        elif what.currentIndex() != k:
            what.setCurrentIndex(k)

    def what_changed(_i):
        if what.currentData() == "multi":
            tabs.setCurrentWidget(box)
        elif tabs.currentWidget() is box:  # the controls are hidden for the other views: leave their tab
            tabs.setCurrentIndex(0)

    tabs.currentChanged.connect(tab_changed)
    what.currentIndexChanged.connect(what_changed)
