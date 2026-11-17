"""Project → Methods text… (plans/architecture.md ARC-11 item 4): the methods paragraph of the project's done runs
in a read-only view with Copy and Save as…, and the BibTeX of the works it names."""

from pathlib import Path

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication, QFileDialog, QPlainTextEdit, QPushButton

from ..core import citations
from ..core.methods import methods
from .kit.dialogs import Dialog

translate = QCoreApplication.translate


def usable(runs):
    """Whether the runs hold a paragraph: the action is enabled only then."""
    return any(r.get("status") == "done" for r in runs)


def texts(runs):
    """(paragraph, BibTeX of the works the paragraph names by their short form)."""
    text = methods(runs)
    keys = [k for k in citations.entries() if citations.short(k) in text]
    return text, citations.bibtex(keys) if keys else ""


class MethodsDialog(Dialog):
    def __init__(self, runs, parent=None, settings=None):
        super().__init__(translate("MethodsDialog", "Methods text"), parent, settings, "methods")
        self.text, self.bib = texts(runs)
        self.view = QPlainTextEdit(self)
        self.view.setReadOnly(True)
        self.view.setPlainText(self.text)
        self.view.setToolTip(translate("MethodsDialog", "The methods paragraph written from the project's done runs"))
        self.body.addWidget(self.view, 3)
        self.bib_view = QPlainTextEdit(self)
        self.bib_view.setReadOnly(True)
        self.bib_view.setPlainText(self.bib)
        self.bib_view.setToolTip(translate("MethodsDialog", "BibTeX of the works the paragraph cites"))
        self.body.addWidget(self.bib_view, 2)
        for name, tip, slot in (
            ("copy_button", translate("MethodsDialog", "Copies the methods text to the clipboard"), self.copy),
            (
                "copy_bib_button",
                translate("MethodsDialog", "Copies the BibTeX entries to the clipboard"),
                self.copy_bib,
            ),
            ("save_button", translate("MethodsDialog", "Saves the methods text as a .txt file"), self.save),
            ("save_bib_button", translate("MethodsDialog", "Saves the BibTeX entries as a .bib file"), self.save_bib),
        ):
            button = QPushButton(self)
            button.setToolTip(tip)
            button.clicked.connect(lambda _=False, s=slot: s())
            self.button_row.addWidget(button)
            setattr(self, name, button)
        self.copy_button.setText(translate("MethodsDialog", "Copy"))
        self.copy_bib_button.setText(translate("MethodsDialog", "Copy BibTeX"))
        self.save_button.setText(translate("MethodsDialog", "Save as…"))
        self.save_bib_button.setText(translate("MethodsDialog", "Save BibTeX as…"))
        self.copy_bib_button.setEnabled(bool(self.bib))
        self.save_bib_button.setEnabled(bool(self.bib))

    def copy(self):
        QApplication.clipboard().setText(self.text)

    def copy_bib(self):
        QApplication.clipboard().setText(self.bib)

    def save(self, path=None):
        return self._save(self.text, path, "methods.txt", "Text (*.txt)")

    def save_bib(self, path=None):
        return self._save(self.bib, path, "references.bib", "BibTeX (*.bib)")

    def _save(self, text, path, name, kind):
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, translate("MethodsDialog", "Save as"), name, kind)
        if not path:
            return None
        try:
            Path(path).write_text(text + "\n", encoding="utf-8")
        except OSError as e:  # no permission, disk full: say so, never crash
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(self, translate("MethodsDialog", "Save as"), str(e))
            return None
        return path
