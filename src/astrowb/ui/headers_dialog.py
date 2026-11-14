"""Edit the headers of many files… (plans/calibration.md CAL-23): the object's name and position, the times and the
airmass computed for every frame, previewed, written into copies — into the files themselves only after a question
that names how many."""

from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
)

from .kit.dialogs import Dialog


class HeadersDialog(Dialog):
    def __init__(self, settings=None, parent=None):
        super().__init__(self.tr("Edit the headers of many files"), parent, settings, "headers")
        self.paths = []
        pick = QPushButton(self.tr("Choose the files…"), self)
        pick.clicked.connect(self.choose)
        self.count = QLabel(self.tr("No file chosen"), self)
        row = QHBoxLayout()
        row.addWidget(pick)
        row.addWidget(self.count, 1)
        self.body.addLayout(row)
        form = QFormLayout()
        self.object, self.ra, self.dec = QLineEdit(self), QLineEdit(self), QLineEdit(self)
        self.object.setPlaceholderText(self.tr("empty: left as it is"))
        self.ra.setPlaceholderText(self.tr("e.g. 13:38:48.1 or 204.70"))
        self.dec.setPlaceholderText(self.tr("e.g. -02:01:49 or -2.03"))
        form.addRow(self.tr("Object (OBJECT)"), self.object)
        form.addRow(self.tr("Right ascension"), self.ra)
        form.addRow(self.tr("Declination"), self.dec)
        self.clock = QDoubleSpinBox(self)
        self.clock.setRange(-86400, 86400)
        self.clock.setDecimals(3)
        self.clock.setSuffix(" s")
        self.clock.setToolTip(self.tr("The camera clock's error, added to every time (e.g. −3600 for a clock left an "
                                      "hour ahead)"))  # fmt: skip
        form.addRow(self.tr("Clock correction"), self.clock)
        self.computed = {}
        boxes = QHBoxLayout()
        for key in ("DATE-AVG", "JD_UTC", "HJD_UTC", "BJD_TDB", "AIRMASS"):
            box = QCheckBox(key, self)
            box.setChecked(key in ("DATE-AVG", "BJD_TDB", "AIRMASS"))
            self.computed[key] = box
            boxes.addWidget(box)
        form.addRow(self.tr("Write"), boxes)
        self.body.addLayout(form)
        self.preview_button = QPushButton(self.tr("Preview"), self)
        self.preview_button.clicked.connect(self.preview)
        self.table = QTableWidget(0, 4, self)
        self.table.setHorizontalHeaderLabels([self.tr("File"), self.tr("Keyword"), self.tr("Now"), self.tr("New")])
        self.copies_button = QPushButton(self.tr("Write copies…"), self)
        self.copies_button.clicked.connect(lambda: self.write())
        self.inplace_button = QPushButton(self.tr("Write into the files…"), self)
        self.inplace_button.clicked.connect(lambda: self.write(in_place=True))
        self.note = QLabel(self)
        self.note.setWordWrap(True)
        for w in (self.preview_button, self.table, self.copies_button, self.inplace_button, self.note):
            self.body.addWidget(w)

    def choose(self, paths=None):
        if paths is None:
            paths = QFileDialog.getOpenFileNames(self, self.tr("Choose the files"), "", "FITS (*.fits *.fit *.fts)")[0]
        self.paths = list(paths)
        self.count.setText(self.tr("{n} files").format(n=len(self.paths)))

    def rules(self):
        from ..planning.target_lists import _angle

        rules = {"computed": [k for k, b in self.computed.items() if b.isChecked()],
                 "clock_offset_s": self.clock.value(), "set": {}}  # fmt: skip
        if self.object.text().strip():
            rules["set"]["OBJECT"] = self.object.text().strip()
        ra, dec = self.ra.text().strip(), self.dec.text().strip()
        if ra and dec:
            ra_deg = _angle(ra, hours=":" in ra or " " in ra or "h" in ra)
            rules["target"] = {"ra": ra_deg, "dec": _angle(dec, hours=False)}
            rules["set"] |= {"RA": round(ra_deg, 6), "DEC": round(rules["target"]["dec"], 6)}
        return rules

    def preview(self):
        from ..calibration.headers import preview
        from .messages import translate

        try:
            rows = preview(self.paths, self.rules())
        except (OSError, ValueError, KeyError) as e:
            self.note.setText(translate(e))
            return []
        self.table.setRowCount(min(len(rows), 500))
        for r, row in enumerate(rows[:500]):
            for c, key in enumerate(("file", "key", "old", "new")):
                self.table.setItem(r, c, QTableWidgetItem("" if row[key] is None else str(row[key])))
        self.note.setText(self.tr("{n} changes in {m} files.").format(n=len(rows), m=len(self.paths)))
        return rows

    def write(self, in_place=False, out_dir=None, confirmed=False):
        from ..calibration.headers import apply
        from .messages import translate

        if not self.paths:
            return []
        if in_place and not confirmed:
            ask = QMessageBox.question(self, self.tr("Write into the files"),
                                       self.tr("Change the headers of {n} files themselves? The old values are not "
                                               "kept.").format(n=len(self.paths)))  # fmt: skip
            if ask != QMessageBox.Yes:
                return []
        if not in_place and out_dir is None:
            out_dir = QFileDialog.getExistingDirectory(self, self.tr("Folder for the copies"))
            if not out_dir:
                return []
        try:
            written = apply(self.paths, self.rules(), out_dir, in_place)
        except (OSError, ValueError, KeyError) as e:
            self.note.setText(translate(e))
            return []
        self.note.setText(self.tr("{n} files written.").format(n=len(written)))
        return written
