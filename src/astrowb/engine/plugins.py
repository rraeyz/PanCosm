"""User plugins: Python files in <config folder>/plugins that register steps with the @step decorator.

    from astrowb.engine.steps import step

    @step("plugin.my_tool", inputs=("image",), outputs=("result",), threshold=5.0)
    def my_tool(inputs, params, ctx):
        \"\"\"One line shown in the Plugins menu.\"\"\"
        ...
        return {"result": ...}

Plugins run with the user's rights like any program they install: only put files there that you trust. A new or
changed file waits until the user allows it (Plugins → Allow…); its SHA-256 is then kept in .trusted.json in the
folder (ARC-22). Files already there when this check first ran, and the bundled examples, are trusted.
A plugin that fails to import is reported and skipped; it never stops the application.
Step ids of plugins must start with "plugin." so they cannot replace built-in steps.
"""

import hashlib
import importlib.util
import json
import sys
import traceback
from pathlib import Path

from .. import settings
from . import steps

_loaded: set[Path] = set()  # plugin files already imported (a file added later is loaded on the next call)
ERRORS: dict[str, str] = {}  # file name -> error text
WAITING: dict[str, Path] = {}  # file name -> path of a new or changed plugin not allowed yet
TRUST = ".trusted.json"  # {file name: sha256} of the allowed plugins, in the plugins folder
PREFIX = "plugin."


def plugin_dir() -> Path:
    return settings.config_dir() / "plugins"


def load_plugins(folder: Path | None = None) -> list[str]:
    """Import every plugin file once; returns the ids of the steps they registered."""
    folder = Path(folder) if folder else plugin_dir()
    files = sorted(folder.glob("*.py")) if folder.is_dir() else []
    trusted = _trusted(folder, files)
    for path in files:
        if path.resolve() in _loaded:
            continue
        if trusted.get(path.name) != _digest(path):
            WAITING[path.name] = path  # never run before the user allows it
            continue
        WAITING.pop(path.name, None)
        _loaded.add(path.resolve())
        before = set(steps.REGISTRY)
        name = f"astrowb_plugin_{path.stem}"
        try:
            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
            bad = [s for s in set(steps.REGISTRY) - before if not s.startswith(PREFIX)]
            for s in bad:
                del steps.REGISTRY[s]
            if bad:
                raise ValueError(f"step ids must start with '{PREFIX}': {', '.join(sorted(bad))}")
        except Exception:  # a broken plugin is reported, never fatal
            ERRORS[path.name] = traceback.format_exc(limit=3)
            sys.modules.pop(name, None)
    return plugin_steps()


def _digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _trusted(folder, files):
    """The allowed plugins' hashes; the first time, every file already in the folder (they ran before this check)."""
    store = Path(folder) / TRUST
    try:
        return json.loads(store.read_text(encoding="utf-8"))
    except FileNotFoundError:
        known = {p.name: _digest(p) for p in files}
        if files:
            store.write_text(json.dumps(known, indent=1), encoding="utf-8")
        return known
    except (OSError, ValueError):
        return {}


def allow(path):
    """Trust this file as it is now (Plugins → Allow…); it loads on the next load_plugins()."""
    path = Path(path)
    store = path.parent / TRUST
    try:
        known = json.loads(store.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        known = {}
    known[path.name] = _digest(path)
    store.write_text(json.dumps(known, indent=1), encoding="utf-8")
    WAITING.pop(path.name, None)


def examples_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "resources" / "plugins"


def install_examples(folder: Path | None = None) -> list[str]:
    """Copy the example plugins into the plugins folder (files already there are kept); returns the new names."""
    import shutil

    folder = Path(folder) if folder else plugin_dir()
    folder.mkdir(parents=True, exist_ok=True)
    copied = []
    for src in sorted(examples_dir().glob("*.py")):
        dest = folder / src.name
        if not dest.exists():
            shutil.copy2(src, dest)
            allow(dest)  # ours, shipped with the program
            copied.append(src.name)
    return copied


def plugin_steps() -> list[str]:
    return sorted(s for s in steps.REGISTRY if s.startswith(PREFIX))
