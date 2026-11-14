"""What can I observe tonight? in the Plan window (plans/planning.md PLN-5): the transiting planets of the Exoplanet
Archive whose transit falls whole in tonight's dark hours above the altitude limit, best first (planning.finder);
asked only when the user presses Fetch, off the window's thread; the chosen ones become targets with their
ephemeris, so the chart shows their transits."""

import threading

import numpy as np
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QDoubleSpinBox, QHBoxLayout, QLabel, QPushButton

from .kit.dialogs import Dialog
from .kit.table_view import DataTable
from .plan_chart import clock


class _Relay(QObject):
    done = Signal(object)


class FinderDialog(Dialog):
    def __init__(self, page, fetch=None):
        super().__init__(self.tr("What can I observe tonight?"), page, getattr(page, "settings", None), "plan_finder")
        self.page, self.fetch, self.events, self.table, self.chosen = page, fetch, [], None, []
        text = self.tr("Transits of known planets that fall whole in tonight's dark hours, above the altitude "
                       "limit. Nothing is asked of the internet until you press Fetch.")  # fmt: skip
        self.note = QLabel(text, self)
        self.note.setWordWrap(True)
        self.mag = QDoubleSpinBox(self)
        self.mag.setRange(5.0, 18.0)
        self.mag.setValue(13.0)
        self.mag.setPrefix(self.tr("V brighter than "))
        self.view = DataTable(self)
        self.view.row_chosen.connect(lambda key: setattr(self, "chosen", [] if key is None else [key]))
        row = QHBoxLayout()
        self.fetch_button = QPushButton(self.tr("Fetch"), self)
        self.fetch_button.clicked.connect(lambda: self.load())
        self.add_button = QPushButton(self.tr("Add as target"), self)
        self.add_button.clicked.connect(self.add_chosen)
        for w in (self.mag, self.fetch_button, self.add_button):
            row.addWidget(w)
        self.body.addWidget(self.note)
        self.body.addLayout(row)
        self.body.addWidget(self.view, 1)
        self.add_buttons(self.tr("Close")).setDefault(True)
        self.resize(max(self.width(), 820), max(self.height(), 480))

    def load(self):
        from ..planning.visibility import Site

        self.note.setText(self.tr("Asking the NASA Exoplanet Archive…"))
        site = Site("", self.page.lat.value(), self.page.lon.value(), self.page.height.value())
        date = self.page.date.date().toString("yyyy-MM-dd")
        min_alt, faint = max(self.page.min_alt.value(), 0.0), self.mag.value()
        self.relay = _Relay(self)
        self.relay.done.connect(self.show_events)

        def work():
            from ..planning.ephemerides import transiting_planets
            from ..planning.finder import tonight_events

            try:
                table = transiting_planets(fetch=self.fetch)
                answer = (table, tonight_events(table, site, date, min_alt=min_alt, mag_range=(-5.0, faint)))
            except Exception as e:  # noqa: BLE001 - the network or the archive: said in the window
                answer = e
            try:
                self.relay.done.emit(answer)
            except RuntimeError:  # the window was closed meanwhile
                pass

        threading.Thread(target=work, daemon=True).start()

    def show_events(self, answer):
        from .messages import translate

        if isinstance(answer, Exception):
            self.note.setText(translate(str(answer)))
            return
        self.table, self.events = answer
        jd = [e["mid"] for e in self.events]
        offset = self.page.local_offset(jd[0]) if jd else 0.0
        self.note.setText(self.tr("{n} transits tonight, best first (local time UTC{off:+g}).").format(
            n=len(self.events), off=offset))  # fmt: skip

        def local(t):
            return clock((t - np.floor(t - 0.5) - 0.5) * 24 + offset)

        header = [self.tr("Planet"), self.tr("Start"), self.tr("Middle"), self.tr("End"), self.tr("V"),
                  self.tr("Depth (mmag)"), self.tr("Moon (°)"), self.tr("Why")]  # fmt: skip
        rows = [[e["name"], local(e["start"]), local(e["mid"]), local(e["end"]), round(e["mag"], 2),
                 round(1000 * e["depth"], 1), round(e["moon"]), e["why"]] for e in self.events]  # fmt: skip
        self.view.set_data(header, rows, keys=list(range(len(self.events))))

    def add_chosen(self):
        """The chosen planet as a target with its ephemeris (t0, period, duration in days)."""
        t = self.table
        out = []
        for i in self.chosen:
            if i >= len(self.events):
                continue
            k = int(np.flatnonzero(t["name"] == self.events[i]["name"])[0])
            out.append({"name": str(t["name"][k]), "ra": float(t["ra"][k]), "dec": float(t["dec"][k]),
                        "t0": float(t["t0"][k]), "period": float(t["period"][k]),
                        "duration": float(t["duration"][k])})  # fmt: skip
        if out:
            self.page._add_list(out)
        return out
