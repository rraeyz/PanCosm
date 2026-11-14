"""Gaia Science Alerts observable tonight, in the Plan window (plans/planning.md PLN-12): the list is asked only when
the user presses Fetch, off the window's thread; the chosen alerts become targets."""

import threading

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton

from .kit.dialogs import Dialog
from .kit.table_view import DataTable


class _Relay(QObject):
    done = Signal(object)


class AlertsDialog(Dialog):
    def __init__(self, page, fetch=None):
        super().__init__(self.tr("Gaia alerts tonight"), page, getattr(page, "settings", None), "plan_alerts")
        self.page, self.fetch, self.rows, self.chosen = page, fetch, [], []
        self.note = QLabel(self.tr("Transients found by Gaia (outbursts, supernovae, microlensing …). Nothing is "
                                   "asked of the internet until you press Fetch."), self)  # fmt: skip
        self.note.setWordWrap(True)
        self.view = DataTable(self)
        self.view.row_chosen.connect(lambda key: setattr(self, "chosen", [] if key is None else [key]))
        row = QHBoxLayout()
        self.fetch_button = QPushButton(self.tr("Fetch"), self)
        self.fetch_button.clicked.connect(lambda: self.load())
        self.add_button = QPushButton(self.tr("Add as target"), self)
        self.add_button.clicked.connect(self.add_chosen)
        for w in (self.fetch_button, self.add_button):
            row.addWidget(w)
        self.body.addWidget(self.note)
        self.body.addWidget(self.view, 1)
        self.body.addLayout(row)
        self.add_buttons(self.tr("Close")).setDefault(True)
        self.resize(max(self.width(), 760), max(self.height(), 460))

    def load(self):
        from ..planning.visibility import Site

        self.note.setText(self.tr("Asking the Gaia alerts page…"))
        site = Site("", self.page.lat.value(), self.page.lon.value(), self.page.height.value())
        date = self.page.date.date().toString("yyyy-MM-dd")
        min_alt = max(self.page.min_alt.value(), 0.0)
        self.relay = _Relay(self)
        self.relay.done.connect(self.show_alerts)

        def work():
            from ..services import feeds_gaia

            try:
                answer = feeds_gaia.observable(feeds_gaia.alerts(fetch=self.fetch), site, date, min_alt)
            except Exception as e:  # noqa: BLE001 - the network or the page: said in the window
                answer = e
            try:
                self.relay.done.emit(answer)
            except RuntimeError:  # the window was closed meanwhile
                pass

        threading.Thread(target=work, daemon=True).start()

    def show_alerts(self, answer):
        from ..services.feeds_gaia import CREDIT
        from .messages import translate

        if isinstance(answer, Exception):
            self.note.setText(translate(str(answer)))
            return None
        self.rows = answer
        self.note.setText(self.tr("{n} alerts above the altitude limit tonight. {credit}").format(
            n=len(answer), credit=CREDIT))  # fmt: skip
        header = [self.tr("Name"), self.tr("Class"), self.tr("Magnitude"), self.tr("Highest (°)"), self.tr("Date"),
                  self.tr("Comment")]  # fmt: skip
        data = [[r["name"], r["cls"], "—" if r["mag"] is None else r["mag"], round(r["max_alt"]), r["date"][:10],
                 r["comment"]] for r in answer]  # fmt: skip
        self.view.set_data(header, data, keys=list(range(len(answer))))
        return None

    def add_chosen(self):
        rows = [self.rows[i] for i in self.chosen if i < len(self.rows)]
        if rows:
            self.page._add_list([{"name": r["name"], "ra": r["ra"], "dec": r["dec"]} for r in rows])
        return rows
