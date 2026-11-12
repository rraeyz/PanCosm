"""Fetch the validation data sets named in data/registry.toml (plans/validation.md VAL-1).

    python tools/fetch_data.py photometry/qatar1-lco      # one set
    python tools/fetch_data.py --area photometry          # every set of an area
    python tools/fetch_data.py --all [--into DIR] [--record]

Files land in data/<id>/ (or $ASTROWB_DATA/<id>/, or --into DIR/<id>/). A file whose SHA-256 matches the registry
is never fetched again; one that does not match is fetched again. --record writes the checksums of the files now
present into the registry (after a first, trusted download). Sets marked "manual" need an account or a form: the
tool says so and points to their SOURCE.md.
"""

import hashlib
import io
import json
import os
import sys
import tarfile
import tomllib
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data" / "registry.toml"


def load(path=REGISTRY):
    return tomllib.loads(Path(path).read_text(encoding="utf-8"))["set"]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _get(url, timeout=120):
    req = urllib.request.Request(url, headers={"User-Agent": "astronomy-workbench-data"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _lco_url(name):
    stem = name.removesuffix(".fz").removesuffix(".fits")
    found = json.loads(_get(f"https://archive-api.lco.global/frames/?basename_exact={stem}"))["results"]
    if not found:
        raise FileNotFoundError(f"{name}: not in the LCO archive")
    return found[0]["url"]


def _from_archive(blob, names, folder):
    """The listed files out of a tar or zip (a member matches by its path's end); returns those found."""
    got = []
    if blob[:2] == b"PK":
        z = zipfile.ZipFile(io.BytesIO(blob))
        members = {m: m for m in z.namelist()}
        read = z.read
    else:
        t = tarfile.open(fileobj=io.BytesIO(blob))
        members = {m.name: m for m in t.getmembers() if m.isfile()}

        def read(m):
            return t.extractfile(members[m]).read()

    for name in names:
        hit = next((m for m in members if m == name or m.endswith("/" + name)), None)
        if hit is not None:
            dest = folder / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(read(hit))
            got.append(name)
    return got


def fetch(entry, base, get=_get, lco_url=_lco_url):
    """Fetch the missing or changed files of one set; returns (fetched, still missing with why)."""
    folder = Path(base) / entry["id"]
    folder.mkdir(parents=True, exist_ok=True)
    sums = entry.get("sha256", {})

    def good(name):
        p = folder / name
        return p.is_file() and (name not in sums or sha256(p) == sums[name])

    todo = [n for n in entry["files"] if not good(n)]
    if not todo:
        return [], []
    kind = entry["source"]
    if kind == "manual":
        return [], [(n, f"get it by hand: data/{entry['id']}/SOURCE.md") for n in todo]
    fetched, missing = [], []
    if kind == "archive":
        try:
            fetched = _from_archive(get(entry["url"]), todo, folder)
        except OSError as e:
            return [], [(n, str(e)) for n in todo]
    else:
        for name in todo:
            try:
                url = lco_url(name) if kind == "lco" else entry["url"] + name
                dest = folder / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                tmp = dest.with_suffix(dest.suffix + ".part")
                tmp.write_bytes(get(url))
                tmp.replace(dest)  # never half a file under the real name
                fetched.append(name)
            except OSError as e:  # unreachable from this network, or gone from the archive
                missing.append((name, str(e)))
    for name in fetched:
        if not good(name):
            missing.append((name, "checksum differs from the registry"))
    missing += [(n, "not in the archive") for n in todo if n not in fetched and n not in dict(missing)]
    return [n for n in fetched if good(n)], missing


def record(entries, base, path=REGISTRY):
    """Write the SHA-256 of every present file into the registry ([set.sha256] tables)."""
    import re

    text = Path(path).read_text(encoding="utf-8")
    for e in entries:
        folder = Path(base) / e["id"]
        sums = {n: sha256(folder / n) for n in e["files"] if (folder / n).is_file()}
        if not sums:
            continue
        block = "[set.sha256]\n" + "".join(f'"{n}" = "{h}"\n' for n, h in sums.items())
        start = text.index(f'id = "{e["id"]}"')
        end = text.find("[[set]]", start)
        end = len(text) if end < 0 else end
        part = re.sub(r"\[set\.sha256\]\n(?:\"[^\n]*\n)*", "", text[start:end]).rstrip("\n") + "\n" + block + "\n"
        text = text[:start] + part + text[end:]
    Path(path).write_text(text, encoding="utf-8")


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    flags = {a for a in argv if a.startswith("--")}
    into = next((argv[i + 1] for i, a in enumerate(argv) if a == "--into"), None)
    base = Path(into or os.environ.get("ASTROWB_DATA") or ROOT / "data")
    entries = load()
    if "--all" not in flags:
        area = next((argv[i + 1] for i, a in enumerate(argv) if a == "--area"), None)
        wanted = set(args) - {into, area}
        entries = [e for e in entries if e["id"] in wanted or e["area"] == area]
    if not entries:
        sys.exit("name a set, --area <area> or --all (data/registry.toml lists them)")
    problems = 0
    for e in entries:
        fetched, missing = fetch(e, base)
        print(f"{e['id']}: {len(fetched)} fetched, {len(e['files']) - len(missing)} of {len(e['files'])} present")
        for name, why in missing:
            print(f"  missing {name}: {why}")
        problems += len(missing)
    if "--record" in flags:
        record(entries, base)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
