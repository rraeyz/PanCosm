"""Native-speaker review of the interface translations through a spreadsheet (PLAN 4.8 item 17b).

    python tools/translation_review.py export de review_de.csv     # every string: English, current text
    python tools/translation_review.py import de review_de.csv     # corrections back into app_de.ts
    python tools/i18n.py                                           # compile
    python tools/translation_review.py glossary                    # astronomy terms kept (glossary.toml)

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


def glossary_problems(lang="tr"):
    """[(source, translation, term, allowed stems)] where a glossary term of the source is not translated with its
    fixed term (plans/architecture.md ARC-18)."""
    import tomllib

    terms = tomllib.loads((I18N / "glossary.toml").read_text(encoding="utf-8")).get(lang, {})
    out = []
    for _ctx, _where, m in _messages(lang):
        source, tr = m.findtext("source") or "", m.find("translation")
        for name in ("astrometry.net", "Period04", "Exoplanet Transit Database"):  # names, not terms
            source = source.replace(name, "")
        if tr is None or tr.get("type") in ("obsolete", "vanished") or not tr.text:
            continue
        # Turkish lower case (I -> ı, İ -> i), without the menu's accelerator mark ("Yö&rünge")
        text = tr.text.replace("&", "").replace("I", "ı").replace("İ", "i").lower()
        for term, stems in terms.items():
            stem = term.endswith("*")
            word = term.rstrip("*")
            # a whole word (plurals too) or a stem, never inside a code example such as isnan(airmass) or flux_err
            ending = "" if stem or not word[-1].isalpha() else r"(?:s|es|'s)?(?![\w(])"
            pattern = r"(?<![\w(])" + re.escape(word) + ending
            if re.search(pattern, source, 0 if word[0].isupper() else re.I) and not any(s in text for s in stems):
                out.append((source, tr.text, term, stems))
    return out


def long_translations(lang="tr", factor=1.6, shortest=12):
    """[(source, translation, ratio)] of translations longer than factor × the English (ARC-18 item 2: where a label
    may be cut); very short sources (a word, a unit) are left out, their ratios mean nothing."""
    out = []
    for _ctx, _where, m in _messages(lang):
        source, tr = m.findtext("source") or "", m.find("translation")
        if tr is None or not tr.text or tr.get("type") in ("obsolete", "vanished") or len(source) < shortest:
            continue
        if len(tr.text) > factor * len(source):
            out.append((source, tr.text, len(tr.text) / len(source)))
    return sorted(out, key=lambda r: -r[2])


def same_translations(lang="tr"):
    """{translation: [sources]} where different English texts got the same translation (ARC-18 item 2): either two
    sources mean the same (fine) or a distinction was lost (look). Case, "&" and a final "…" are ignored."""
    by = {}
    for _ctx, _where, m in _messages(lang):
        source, tr = m.findtext("source") or "", m.find("translation")
        if tr is None or not tr.text or tr.get("type") in ("obsolete", "vanished"):
            continue
        by.setdefault(tr.text, set()).add(source)

    def key(text):
        return text.replace("&", "").rstrip("…").strip().casefold()

    return {t: sorted(s) for t, s in by.items() if len({key(x) for x in s}) > 1}


if __name__ == "__main__" and sys.argv[1:2] == ["same"]:
    found = same_translations(sys.argv[2] if len(sys.argv) > 2 else "tr")
    for tr, sources in found.items():
        print(f"{tr}\n" + "".join(f"    {s}\n" for s in sources))
    print(f"{len(found)} translations stand for more than one English text")
elif __name__ == "__main__" and sys.argv[1:2] == ["long"]:
    found = long_translations(sys.argv[2] if len(sys.argv) > 2 else "tr")
    for source, tr, ratio in found:
        print(f"{ratio:.2f}×  {source}\n       {tr}")
    print(f"{len(found)} translations longer than 1.6 × the English")
elif __name__ == "__main__" and sys.argv[1:2] == ["glossary"]:
    found = glossary_problems()
    for source, tr, term, stems in found:
        print(f"{term} -> {' / '.join(stems)}\n  {source}\n  {tr}\n")
    print(f"{len(found)} strings do not use the glossary's term")
    sys.exit(1 if found else 0)
elif __name__ == "__main__":
    main()
