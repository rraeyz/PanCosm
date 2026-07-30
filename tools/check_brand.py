"""Fail if the product name appears anywhere outside the brand folder.

Reads the current names from brand.toml, so it keeps working after a rename.
Usage: python tools/check_brand.py   (exit code 1 lists offending lines)
"""

import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRAND_DIR = "src/astrowb/resources/brand/"
ALLOWED = {"README.md"}


def brand_terms() -> list[str]:
    b = tomllib.loads((ROOT / BRAND_DIR / "brand.toml").read_text(encoding="utf-8"))["brand"]
    words = {b["display_name"], b["short_name"], b["app_id"], *b["organization"].split()}
    words |= set(b["bundle_id"].split(".")) | set(b["windows_app_user_model_id"].split("."))
    words |= set(b.get("previous_app_ids", []))
    generic = {"org", "com", "net", "io", "app", "desktop", "project", "the"}
    return sorted(w for w in words if len(w) >= 4 and w.lower() not in generic)


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [f for f in out.splitlines() if not f.startswith(BRAND_DIR) and f not in ALLOWED]


def find_violations() -> list[str]:
    pattern = re.compile("|".join(map(re.escape, brand_terms())), re.IGNORECASE)
    hits = []
    for rel in tracked_files():
        if pattern.search(rel):
            hits.append(f"{rel}: file name")
        path = ROOT / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_bytes().decode("latin-1")
        for n, line in enumerate(text.splitlines(), 1):
            if pattern.search(line):
                hits.append(f"{rel}:{n}: {line.strip()[:100]}")
    return hits


if __name__ == "__main__":
    violations = find_violations()
    for v in violations:
        print(v)
    if violations:
        print(
            f"\n{len(violations)} brand-name occurrence(s) outside {BRAND_DIR}. Read the name from brand.toml instead."
        )
    sys.exit(1 if violations else 0)
