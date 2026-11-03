"""Native-speaker review of the interface translations through a spreadsheet (PLAN 4.8 item 17b).

    python tools/translation_review.py export de review_de.csv     # every string: English, current text
    python tools/translation_review.py import de review_de.csv     # corrections back into app_de.ts
    python tools/i18n.py                                           # compile

The CSV opens in LibreOffice / Excel. The reviewer writes a better text in the column "corrected" (and, if useful,
a note in "comment"); rows left empty keep the current translation. Placeholders in braces ({n}, {app}, ...) must
stay as they are: a correction that loses or adds one is refused and listed. The guide pages are Markdown files in
src/astrowb/resources/guide/<language>/ and are reviewed as text.
"""

import csv
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
I18N = ROOT / "src" / "astrowb" / "resources" / "i18n"
FIELDS = ["context", "where", "english", "turkish", "current", "corrected", "comment"]


def _messages(lang):
    root = ET.parse(I18N / f"app_{lang}.ts").getroot()
    for ctx in root.iter("context"):
        name = ctx.findtext("name")
        for m in ctx.iter("message"):
            loc = m.find("location")
            where = f"{loc.get('filename', '').replace('../../', '')}:{loc.get('line', '')}" if loc is not None else ""
            yield name, where, m


def export(lang, out):
    turkish = {(c, m.findtext("source")): m.findtext("translation") or "" for c, _, m in _messages("tr")}
    rows = []
    for ctx, where, m in _messages(lang):
        tr = m.find("translation")
        if tr.get("type") in ("obsolete", "vanished"):
            continue
        src = m.findtext("source")
        rows.append([ctx, where, src, turkish.get((ctx, src), ""), tr.text or "", "", ""])
    with open(out, "w", newline="", encoding="utf-8-sig") as f:  # BOM: Excel opens UTF-8 correctly
        w = csv.writer(f)
        w.writerow(FIELDS)
        w.writerows(rows)
    print(f"{len(rows)} strings written to {out}")


def _placeholders(text):
    return sorted(re.findall(r"\{[^}]*\}", text))


def apply(lang, path):
    """Corrections from the CSV into app_<lang>.ts. Returns (changed, refused [(english, reason)])."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        fixes = {(r["context"], r["english"]): r["corrected"] for r in csv.DictReader(f) if r["corrected"].strip()}
    ts = I18N / f"app_{lang}.ts"
    tree = ET.parse(ts)
    changed, refused = 0, []
    for ctx in tree.getroot().iter("context"):
        name = ctx.findtext("name")
        for m in ctx.iter("message"):
            src = m.findtext("source")
            new = fixes.pop((name, src), None)
            if new is None:
                continue
            if _placeholders(new) != _placeholders(src):
                refused.append((src, f"placeholders {_placeholders(src)} must stay; got {_placeholders(new)}"))
                continue
            tr = m.find("translation")
            if tr.text != new or tr.get("type"):
                tr.text = new
                tr.attrib.pop("type", None)
                changed += 1
    refused += [(src, "no such string (the program changed since the export?)") for _, src in fixes]
    tree.write(ts, encoding="utf-8", xml_declaration=True)
    return changed, refused


def main():
    if len(sys.argv) != 4 or sys.argv[1] not in ("export", "import"):
        sys.exit(__doc__)
    cmd, lang, path = sys.argv[1:]
    if cmd == "export":
        export(lang, path)
        return
    changed, refused = apply(lang, path)
    subprocess.run([sys.executable, str(ROOT / "tools" / "i18n.py"), "update"], check=True)  # lupdate's layout
    print(f"{changed} translations corrected")
    for src, why in refused:
        print(f"refused: {src!r}: {why}")


if __name__ == "__main__":
    main()
