"""Help → Licences of the libraries… (plans/interface.md UI-17): every library inside the program with its version
and licence, read from the installed packages' own metadata, so the list is always that of this build (the LGPL
asks that the user is told Qt is used and under which licence)."""

from importlib.metadata import distributions

from PySide6.QtCore import QCoreApplication

OWN = {"astrowb", "pip", "setuptools", "wheel", "pyinstaller", "pyinstaller-hooks-contrib"}


def licence_of(dist):
    """The licence a package states: its licence expression, its classifiers, or the first line of its licence."""
    md = dist.metadata
    parts = [md.get("License-Expression") or ""]
    parts += [c.split("::")[-1].strip() for c in md.get_all("Classifier") or [] if c.startswith("License ::")]
    if not any(parts) and md.get("License"):
        parts.append(md.get("License").splitlines()[0][:80])
    return "; ".join(p for p in parts if p) or "see the package"


def rows():
    """[(name, version, licence)] of the libraries in the program, by name."""
    found = {}
    for dist in distributions():
        name = dist.metadata["Name"] or ""
        if name and name.lower() not in OWN:
            found[name.lower()] = (name, dist.version, licence_of(dist))
    return [found[k] for k in sorted(found)]


def show(parent):
    from astropy.table import Table

    from .kit.dialogs import Dialog
    from .kit.table import TableView

    translate = QCoreApplication.translate
    dialog = Dialog(translate("MainWindow", "Licences of the libraries"), parent)
    found = rows()
    view = TableView(dialog)
    names = (translate("MainWindow", "Library"), translate("MainWindow", "Version"), translate("MainWindow", "Licence"))
    view.set_table(Table(rows=found or None, names=names) if found else Table(names=names, dtype=(str, str, str)))
    dialog.body.addWidget(view)
    dialog.resize(720, 520)
    dialog.show()
    return dialog
