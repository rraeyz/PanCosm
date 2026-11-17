"""Automation window: "Schedule…" runs the automation at a local time (plans/interface.md UI-16.12)."""

from datetime import datetime, timedelta

from PySide6.QtCore import QCoreApplication, QTime, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

translate = QCoreApplication.translate


def add_schedule_button(page):
    """The button and the "Scheduled: 22:30 [Cancel]" line go under the template button."""
    b = page.schedule_button = QPushButton(translate("AutomationSchedule", "Schedule…"), page)
    b.setToolTip(translate("AutomationSchedule", "Runs the automation at a time you choose"))
    b.clicked.connect(lambda: schedule_dialog(page))
    row = page.schedule_row = QWidget(page)
    lay = QHBoxLayout(row)
    lay.setContentsMargins(0, 0, 0, 0)
    page.schedule_label = QLabel(row)
    cancel = page.schedule_cancel = QPushButton(translate("AutomationSchedule", "Cancel"), row)
    cancel.setToolTip(translate("AutomationSchedule", "Drop the scheduled run"))
    cancel.clicked.connect(lambda: cancel_schedule(page))
    lay.addWidget(page.schedule_label, 1)
    lay.addWidget(cancel)
    row.setVisible(False)
    page.schedule_timer = None
    left = page.list.parentWidget().layout()
    left.insertWidget(left.count(), b)
    left.insertWidget(left.count(), row)


def next_delay_ms(at, now=None):
    """Milliseconds from `now` to the next time the clock shows `at` (a QTime): today, else tomorrow."""
    now = now or datetime.now()
    target = now.replace(hour=at.hour(), minute=at.minute(), second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return int((target - now).total_seconds() * 1000)


def schedule_dialog(page):
    d = QDialog(page)
    d.setWindowTitle(translate("AutomationSchedule", "Schedule"))
    lay = QVBoxLayout(d)
    # shortcut: the schedule lives in a QTimer of the page, so closing the program forgets it; a stored
    # schedule that a background service runs is not built yet
    note = QLabel(
        translate(
            "AutomationSchedule",
            "Runs the automation at this local time (today, or tomorrow if it has passed). "
            "The schedule is lost when the program closes. To run after the night's sequence, "
            'tick "Process after the sequence" instead.',
        ),
        d,
    )
    note.setWordWrap(True)
    edit = QTimeEdit(QTime.currentTime().addSecs(3600), d)
    edit.setDisplayFormat("HH:mm")
    box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, d)
    box.accepted.connect(d.accept)
    box.rejected.connect(d.reject)
    for w in (note, edit, box):
        lay.addWidget(w)
    if d.exec() == QDialog.Accepted:
        schedule_at(page, edit.time())


def schedule_at(page, at, delay_ms=None):
    """Start the single-shot timer for the QTime `at` (`delay_ms` overrides the wait, for tests)."""
    cancel_schedule(page)
    t = page.schedule_timer = QTimer(page)
    t.setSingleShot(True)
    t.timeout.connect(lambda: _fire(page))
    t.start(next_delay_ms(at) if delay_ms is None else delay_ms)
    page.schedule_label.setText(translate("AutomationSchedule", "Scheduled: {time}").format(time=at.toString("HH:mm")))
    page.schedule_row.setVisible(True)


def cancel_schedule(page):
    if page.schedule_timer is not None:
        page.schedule_timer.stop()
        page.schedule_timer.deleteLater()
        page.schedule_timer = None
    page.schedule_row.setVisible(False)


def _fire(page):
    cancel_schedule(page)
    from .automation_run import run_state

    if run_state(page).running:  # _run would stop a run that is going
        page.status.setText(translate("AutomationSchedule", "Scheduled run skipped: a run is already going"))
        return
    page.unattended = True  # nobody is there to answer the run plan
    page._run()
