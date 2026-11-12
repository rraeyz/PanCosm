"""VAL-1: data/registry.toml names every validation data set and its exact files, as the SOURCE.md notes do; the
fetch tool skips a verified file, fetches a missing or changed one again and reports what it cannot get."""

import hashlib
import importlib.util
import io
import re
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _tool():
    spec = importlib.util.spec_from_file_location("fetch_data", ROOT / "tools" / "fetch_data.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_registry_and_source_notes_agree():
    sets = {e["id"]: e for e in _tool().load()}
    notes = {str(p.parent.relative_to(ROOT / "data")): p for p in (ROOT / "data").rglob("SOURCE.md")}
    assert set(sets) == set(notes), "a set without its note, or a note without its set"
    for sid, note in notes.items():
        listed = re.findall(r"^- `([^`]+)`", note.read_text().split("## Files used in the checks", 1)[-1], re.M)
        assert sets[sid]["files"] == listed, sid
        assert sets[sid]["source"] in ("lco", "url", "archive", "manual")
        assert set(sets[sid].get("sha256", {})) <= set(listed), sid


def test_fetch_verifies_refetches_and_reports(tmp_path):
    tool = _tool()
    body = b"frame data"
    entry = {"id": "photometry/x", "source": "url", "url": "https://example.org/", "files": ["a.fits", "b.fits"],
             "sha256": {"a.fits": hashlib.sha256(body).hexdigest()}}  # fmt: skip
    calls = []

    def get(url):
        calls.append(url)
        if url.endswith("b.fits"):
            raise OSError("unreachable from this network")
        return body

    fetched, missing = tool.fetch(entry, tmp_path, get=get)
    assert fetched == ["a.fits"] and missing == [("b.fits", "unreachable from this network")]
    calls.clear()
    tool.fetch(entry, tmp_path, get=get)
    assert calls == ["https://example.org/b.fits"]  # a verified file is never fetched again
    (tmp_path / "photometry/x/a.fits").write_bytes(b"corrupted")
    tool.fetch(entry, tmp_path, get=get)
    assert (tmp_path / "photometry/x/a.fits").read_bytes() == body  # a changed file is fetched again
    manual = {"id": "spectroscopy/y", "source": "manual", "files": ["z.fits"]}
    assert "SOURCE.md" in tool.fetch(manual, tmp_path)[1][0][1]


def test_files_come_out_of_an_archive(tmp_path):
    tool = _tool()
    blob = io.BytesIO()
    with tarfile.open(fileobj=blob, mode="w:gz") as t:
        for name in ("night/ccd.001.0.fits", "night/darks/ccd.013.0.fits", "night/other.fits"):
            info = tarfile.TarInfo(name)
            info.size = 3
            t.addfile(info, io.BytesIO(b"abc"))
    entry = {
        "id": "calibration/z",
        "source": "archive",
        "url": "u",
        "files": ["ccd.001.0.fits", "darks/ccd.013.0.fits"],
    }
    fetched, missing = tool.fetch(entry, tmp_path, get=lambda url: blob.getvalue())
    assert sorted(fetched) == ["ccd.001.0.fits", "darks/ccd.013.0.fits"] and not missing
    assert not (tmp_path / "calibration/z/other.fits").exists()
