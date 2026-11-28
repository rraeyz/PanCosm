"""Observe page: loading and starting sequences, night plans and flats."""

from pathlib import Path

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QPushButton

from .messages import translate


class SequenceActions:
    """Mixed into ObservePage; its texts are translated in the ObservePage context."""

    def load_schedule(self, blocks):
        """A night plan: one sequence target per block, observed between its start and end."""
        from astropy.time import Time

        self.plan = [
            {
                "name": b["name"],
                "ra": b["ra"],
                "dec": b["dec"],
                "start": Time(b["start"], format="jd").isot[:19],
                "end": Time(b["end"], format="jd").isot[:19],
            }
            for b in blocks
        ]
        self.plan_list.clear()
        self.plan_list.addItems(f"{t['start'][11:16]}–{t['end'][11:16]} UTC  {t['name']}" for t in self.plan)
        self.plan_box.setVisible(bool(self.plan))

    def load_sequence(self, target):
        """Fill the sequence form from a target spec (as sequence_spec writes it, e.g. from an automation)."""
        from astropy.coordinates import SkyCoord

        self.seq_name.setText(target.get("name", ""))
        coord = ""
        if "ra" in target:
            coord = SkyCoord(target["ra"], target["dec"], unit="deg").to_string("hmsdms", sep=":", precision=1)
        self.seq_coord.setText(coord)
        self.dither.setValue(int(target.get("dither_every", 0)))
        self.seq_start.setText(target.get("start") or "")
        self.seq_end.setText(target.get("end") or "")
        self.edit(
            QCoreApplication.translate("ObservePage", "load a sequence"), self._load_rows, target.get("exposures", [])
        )
        self.rotation.setText("" if target.get("rotation") is None else str(target["rotation"]))

    def _load_rows(self, exposures):
        self.exposures.setRowCount(0)
        for e in exposures:
            self.add_exposure_row()
            r = self.exposures.rowCount() - 1
            self.exposures.cellWidget(r, 0).setCurrentText(e.get("kind", "light"))
            self.exposures.item(r, 1).setText(e.get("filter") or "")
            self.exposures.cellWidget(r, 2).setValue(float(e.get("exptime", 60)))
            self.exposures.cellWidget(r, 3).setValue(int(e.get("count", 1)))
            self.exposures.cellWidget(r, 4).setValue(int(e.get("binning", 1)))
            for c, key in ((5, "gain"), (6, "offset"), (7, "readout")):
                self.exposures.item(r, c).setText("" if e.get(key) is None else str(e[key]))
            self.exposures.item(r, 8).setText(", ".join(str(v) for v in e.get("roi") or []))

    def _start_sequence(self):
        try:
            spec = self.sequence_spec()
        except ValueError as e:
            self.job.setText(translate(e))
            return
        if self._post("/sequence", spec):
            self._sequence_dir = spec["out_dir"]
            if hasattr(self, "follow_button"):
                self.follow_button.setEnabled(True)

    def panel_flats(self):
        r = max(self.exposures.currentRow(), 0)
        item = self.exposures.item(r, 1)
        return self._post(
            "/panelflats",
            {
                "filter": (item.text().strip() if item else "") or None,
                "count": self.exposures.cellWidget(r, 3).value(),
                "out_dir": self.out_dir.text().strip(),
            },
        )

    def _sky_flats(self):
        r = max(self.exposures.currentRow(), 0)
        item = self.exposures.item(r, 1)
        self._post(
            "/skyflats",
            {
                "filter": (item.text().strip() if item else "") or None,
                "count": self.exposures.cellWidget(r, 3).value(),
                "out_dir": self.out_dir.text().strip(),
            },
        )


def add_follow_button(page, main):
    """PHO-19 item 4: the running sequence's folder followed live in the Photometry window."""
    b = page.follow_button = QPushButton(QCoreApplication.translate("ObservePage", "Measure live in Photometry"), page)
    b.setToolTip(
        QCoreApplication.translate(
            "ObservePage", "Opens Photometry following the folder this sequence saves its frames in"
        )
    )
    b.setEnabled(False)
    b.clicked.connect(lambda: follow_in_photometry(page, main))
    page.job.parentWidget().layout().addWidget(b)


def follow_in_photometry(page, main):
    folder = getattr(page, "_sequence_dir", None)
    if not folder or not Path(folder).is_dir():
        page.job.setText(
            QCoreApplication.translate("ObservePage", "No frames yet: the sequence's folder does not exist")
        )
        return False
    main.open_area("photometry")
    photometry = main.photometry_page
    if not photometry.coord.text().strip():
        photometry.coord.setText(page.seq_name.text().strip())
    return photometry.start_live(folder)
