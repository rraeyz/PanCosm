"""Automations: a named chain of steps saved as JSON, built by the user or started from a ready template.

    {"name": "...", "description": "...",
     "inputs": {"folder": {"kind": "folder", "label": "..."}},      # how to ask for user inputs (optional)
     "sequence": {...},                                             # optional observing part (Observe page)
     "steps": [{"step": "calibration.run",
                "inputs": {"images": "calibrated"},                 # step input <- data key (default: same name)
                "params": {"sigma": 3.0},
                "each": "science"}]}                                # optional: run once per item of that input

A link is a data key, "key.field" (that field of a result, or of every row of a list of results), or a
format string such as "{output_dir}/{item}_1d.fits" (item: file stem of the current "each" element).
Names, descriptions and labels may be {"en": ..., "tr": ...} so templates are translated.
Outputs of an "each" step are lists, one value per item. Every step runs as a normal recorded task.
"""

import json
import string
from pathlib import Path

from ..settings import config_dir
from . import steps

TEMPLATES = Path(__file__).resolve().parents[1] / "resources" / "automations"
KINDS = ("folder", "file", "files", "xy", "pairs", "site", "number", "text")


def user_dir() -> Path:
    return config_dir() / "automations"


def load(path) -> dict:
    auto = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(auto.get("steps"), list):
        raise ValueError(f"{path}: not an automation (no step list)")
    auto["path"] = str(path)
    return auto


def save(auto, path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {k: v for k, v in auto.items() if k != "path"}
    path.write_text(json.dumps(body, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def available() -> list[dict]:
    """Ready templates, then the user's own automations (a broken file is skipped, never fatal)."""
    found = []
    for folder, template in ((TEMPLATES, True), (user_dir(), False)):
        for p in sorted(folder.glob("*.json")) if folder.is_dir() else ():
            try:
                found.append(load(p) | {"template": template})
            except (ValueError, OSError):
                continue
    return found


def text(value, lang="en"):
    """A plain string, or the entry for `lang` of a {"en": ..., "tr": ...} dict (English as fallback)."""
    return value.get(lang) or value.get("en", "") if isinstance(value, dict) else (value or "")


def _keys(link):
    if "{" in link:
        return [f for _, f, _, _ in string.Formatter().parse(link) if f and f != "item"]
    return [link.split(".")[0]]


def needed(auto, available=()) -> list[str]:
    """Data keys the user must provide: required step inputs that no earlier step produces."""
    have, need = set(available), []
    for entry in auto["steps"]:
        s = steps.get(entry["step"])
        links = entry.get("inputs", {})
        for name in s.inputs:
            need += [k for k in _keys(links.get(name, name)) if k not in have and k not in need]
        have.update(s.outputs)
    return need


def check(auto, inputs) -> None:
    """Fail before anything runs: unknown step, no steps, or inputs nobody provides."""
    if not auto["steps"]:
        raise ValueError("the automation has no steps")
    for entry in auto["steps"]:
        try:
            steps.get(entry["step"])
        except KeyError:
            raise ValueError(f"unknown step {entry['step']} (a plugin that is not installed?)") from None
    missing = needed(auto, inputs)
    if missing:
        raise steps.MissingInput(auto["steps"][0]["step"], missing)


def _value(data, link, item):
    if "{" in link:
        return link.format(**{k: v for k, v in data.items() if isinstance(v, str | int | float)}, item=item)
    if link in data:
        return data[link]
    head, _, field = link.partition(".")
    value = data[head]
    return [row[field] for row in value] if isinstance(value, list) else value[field]


def calls(auto, inputs):
    """Generator of (step_id, inputs, params), one per task; send each task's outputs back.
    Its return value (StopIteration.value) is all data at the end."""
    check(auto, inputs)
    data = dict(inputs)
    for entry in auto["steps"]:
        s = steps.get(entry["step"])
        links, each = entry.get("inputs", {}), entry.get("each")
        items = _value(data, links.get(each, each), None) if each else [None]
        collected = {}
        for item in items:
            stem = Path(str(item)).name.split(".")[0] if each else ""
            args = {}
            for name in s.inputs + s.optional:
                link = links.get(name, name)
                if name == each:
                    args[name] = item
                elif "{" in link or link.split(".")[0] in data:
                    args[name] = _value(data, link, stem)
            out = yield entry["step"], args, entry.get("params", {})
            for key, value in out.items():
                collected.setdefault(key, []).append(value)
            if not each:
                collected = out
        data.update(collected)
    return data


def run(engine, auto, inputs) -> dict:
    """Run the whole automation, blocking (tests, scripts). The UI drives `calls` task by task instead."""
    gen = calls(auto, inputs)
    call = next(gen)
    try:
        while True:
            call = gen.send(engine.run_step(*call).result())
    except StopIteration as stop:
        return stop.value


def parse(kind, value):
    """A user's text for an input of `kind` -> the value the steps expect."""
    value = value.strip()
    numbers = [float(v) for v in value.replace(",", " ").replace(";", " ").split()] if kind in ("xy", "site") else []
    if kind == "files":
        return [p.strip() for p in value.replace("\n", ";").split(";") if p.strip()]
    if kind == "xy":
        if len(numbers) != 2:
            raise ValueError("two numbers expected: x y")
        return numbers
    if kind == "pairs":
        rows = [[float(v) for v in r.replace(",", " ").split()] for r in value.split(";") if r.strip()]
        if any(len(r) != 2 for r in rows):
            raise ValueError("pairs expected: a b; c d; ...")
        return rows
    if kind == "site":
        if len(numbers) not in (2, 3):
            raise ValueError("latitude longitude [height in m] expected")
        return {"name": "site", "lat": numbers[0], "lon": numbers[1], "height": numbers[2] if len(numbers) > 2 else 0.0}
    if kind == "number":
        return float(value)
    return value
