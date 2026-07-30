"""Fill unfinished translations in a .ts file in place, keeping lupdate's formatting.

python tools/i18n.py update
python tools/fill_translations.py src/astrowb/resources/i18n/app_tr.ts "Source text=>Çeviri" ...
python tools/i18n.py            # compile to .qm
"""

import html
import re
import sys

path, pairs = sys.argv[1], dict(a.split("=>", 1) for a in sys.argv[2:])
text = open(path, encoding="utf-8").read()
n = 0


def repl(m):
    global n
    src = html.unescape(m.group(1))
    if src not in pairs:
        return m.group(0)
    n += 1
    return re.sub(
        r'<translation type="unfinished">[^<]*</translation>',
        f"<translation>{html.escape(pairs[src], quote=False)}</translation>",
        m.group(0),
    )


text = re.sub(
    r'<source>([^<]*)</source>\s*(?:<comment>[^<]*</comment>\s*)?<translation type="unfinished">[^<]*</translation>',
    repl,
    text,
)
open(path, "w", encoding="utf-8").write(text)
print("filled", n)
