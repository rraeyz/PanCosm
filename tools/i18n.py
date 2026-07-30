"""Translations.  python tools/i18n.py          -> compile .ts to .qm
                 python tools/i18n.py update   -> extract new strings from the code into the .ts files

Add a language: copy resources/i18n/app_tr.ts to app_<code>.ts, set its language attribute,
translate it in Qt Linguist (pyside6-linguist), and add the code to ui/i18n.py LANGUAGES.
The product name is never written into a translation: strings use the {app} placeholder.
The training guide is translated the same way: add resources/guide/<code>/ with the same .md files, add the
language to the automation templates (resources/automations/*.json) and run tools/guide_screenshots.py <code>.
"""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "astrowb"
I18N = SRC / "resources" / "i18n"


def tool(name):
    exe = shutil.which(f"pyside6-{name}")
    if not exe:
        sys.exit(f"pyside6-{name} not found; install PySide6")
    return exe


def update():
    sources = [str(p) for p in sorted(SRC.rglob("*.py"))]
    for ts in sorted(I18N.glob("app_*.ts")):
        subprocess.run([tool("lupdate"), "-no-obsolete", *sources, "-ts", str(ts)], check=True)


def build():
    for ts in sorted(I18N.glob("app_*.ts")):
        subprocess.run([tool("lrelease"), str(ts), "-qm", str(ts.with_suffix(".qm"))], check=True)


if __name__ == "__main__":
    update() if sys.argv[1:] == ["update"] else build()
