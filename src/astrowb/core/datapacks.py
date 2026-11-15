"""The data the program downloads or caches into the user's folder, as a list the Settings → Data page shows: what
is there, how big, where, and a way to remove it (ARC-20 item 1).

There is no pack server: each kind is fetched by the step that needs it, on first use, from the address that step's
module names (SOURCES). So this manager lists, measures and removes; the next use downloads again.

    for p in packs(base): p["id"], p["size"], p["path"], p["source"]
    remove(base, "pickles")       # base: the settings folder (settings.path.parent)
"""

from pathlib import Path

# id -> (folder under base, file pattern); the order is the order shown
PACKS = {
    "pickles": ("templates", "pickles_uk_*.fits"),
    "mk": ("templates/mk_libnor36", "*"),
    "phoenix": ("phoenix", "*"),
    "earth": ("earth-orientation", "*"),
    "answers": ("cache", "*"),
}


def source(pack_id):
    """The address(es) the program downloads the pack from (empty for the answer cache)."""
    if pack_id == "pickles":
        from ..spectroscopy.templates import PICKLES_URL

        return [PICKLES_URL.rsplit("/", 1)[0] + "/"]
    if pack_id == "mk":
        from ..spectroscopy.mkstandards import MK_URL

        return [MK_URL]
    if pack_id == "phoenix":
        from ..spectroscopy.atmosphere import KURUCZ_SUN, PHOENIX

        return [PHOENIX, KURUCZ_SUN]
    return []


def _files(base, pack_id):
    folder, pattern = PACKS[pack_id]
    root = Path(base) / folder
    return [p for p in root.rglob(pattern) if p.is_file()] if root.is_dir() else []


def packs(base):
    """[{id, path, files, size, source}] for every kind, present or not (size 0: nothing stored)."""
    out = []
    for pack_id, (folder, _pattern) in PACKS.items():
        found = _files(base, pack_id)
        out.append({"id": pack_id, "path": str(Path(base) / folder), "files": len(found),
                    "size": sum(p.stat().st_size for p in found), "source": source(pack_id)})  # fmt: skip
    return out


def remove(base, pack_id):
    """Delete the pack's files (nothing else in the folder); returns how many. An unknown id is a ValueError."""
    if pack_id not in PACKS:
        raise ValueError(f"unknown data pack {pack_id}")
    found = _files(base, pack_id)
    for p in found:
        p.unlink(missing_ok=True)
    root = Path(base) / PACKS[pack_id][0]
    for d in sorted((d for d in root.rglob("*") if d.is_dir()), reverse=True) + [root]:
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()  # folders the removal emptied; a shared folder with other files stays
    return len(found)
