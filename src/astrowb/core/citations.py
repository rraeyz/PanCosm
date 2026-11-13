"""What to cite for each method (plans/architecture.md ARC-11 item 3): `@cites("key", …)` beside the code that uses
a published method; the BibTeX entries live in resources/citations/citations.bib. The methods text and a paper's
reference list are made from the keys of the steps that ran."""

import re
from functools import cache
from pathlib import Path

BIB = Path(__file__).resolve().parent.parent / "resources" / "citations" / "citations.bib"
USED = {}  # "module.function" -> keys


def cites(*keys):
    """Marks a function as an implementation of the methods in keys (BibTeX keys)."""

    def mark(fn):
        fn.__cites__ = tuple(keys)
        USED[f"{fn.__module__}.{fn.__qualname__}"] = tuple(keys)
        return fn

    return mark


@cache
def entries():
    """{key: BibTeX entry text} from the bundled file."""
    text = BIB.read_text(encoding="utf-8")
    starts = [m.start() for m in re.finditer(r"^@\w+\{", text, re.M)] + [len(text)]
    out = {}
    for a, b in zip(starts, starts[1:], strict=False):
        chunk = text[a:b].strip()
        out[re.match(r"@\w+\{([^,]+),", chunk).group(1)] = chunk
    return out


def short(key):
    """'Kwee & van Woerden (1956)' style text of one entry."""
    e = entries()[key]
    authors = re.search(r"author = \{(.*)\},\n", e).group(1)
    year = re.search(r"year = (\d{4})", e).group(1)
    names = [re.sub(r"[{}\\\"']", "", a.split(",")[0]).strip() for a in authors.split(" and ")]
    names = [n for n in names if n != "others"]
    if len(names) == 1 and "others" not in authors:
        who = names[0]
    elif len(names) == 2 and "others" not in authors:
        who = f"{names[0]} & {names[1]}"
    else:
        who = f"{names[0]} et al."
    return f"{who} ({year})"


def bibtex(keys):
    """The BibTeX entries of the keys, each once, in the order given."""
    return "\n".join(entries()[k] for k in dict.fromkeys(keys)) + "\n"
