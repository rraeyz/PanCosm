"""Session state of an area window: one tree of plain values, changed only through the store, so that undo / redo,
autosave and "continue where you left off" all come from the same place (plans/architecture.md ARC-5).

The state is a JSON-like tree (dict, list, str, int, float, bool, None; numpy arrays are allowed for small data and
are stored as lists). A path names a place in it: "apertures.r_ap", "stars.2.role" (list items by index).

    store = Store("photometry", {"apertures": {"r_ap": 6.0}})
    store.set("apertures.r_ap", 7.0, text="aperture radius")      # one undoable change
    with store.batch("suggest comparison stars"):                  # several changes, one undo step
        store.set("stars", [...]); store.set("comparisons", [...])
    store.undo(); store.redo()
    store.subscribe(lambda paths: ...)                             # called with the changed paths
    text = store.to_json(); Store.from_json(text)                  # with the schema and migrations

Consecutive changes of the same path within MERGE_SECONDS merge into one undo step (typing, dragging a slider).
No Qt here: the window binds its controls to paths (ui/kit/binding.py) and turns the stack into Edit menu entries.
"""

import copy
import json
import time
from contextlib import contextmanager

MERGE_SECONDS = 0.7
_MISSING = object()
MIGRATIONS = {}  # (area, schema) -> function(tree) -> tree of schema + 1


def migration(area, from_schema):
    """Register a function that turns a state of `from_schema` into `from_schema + 1` for an area."""

    def register(function):
        MIGRATIONS[(area, from_schema)] = function
        return function

    return register


def _plain(value):
    """A copy made only of JSON values (numpy arrays and tuples become lists, numpy numbers Python numbers)."""
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if hasattr(value, "tolist"):  # numpy arrays and scalars
        return value.tolist()
    return copy.deepcopy(value)


def _keys(path):
    return [int(k) if k.lstrip("-").isdigit() else k for k in path.split(".")] if path else []


def get(tree, path, default=None):
    node = tree
    for k in _keys(path):
        try:
            node = node[k]
        except (KeyError, IndexError, TypeError):
            return default
    return node


def _copy(value):
    return value if value is _MISSING else copy.deepcopy(value)


def _put(tree, path, value):
    """Set value at path (creating dicts on the way); returns the old value or _MISSING."""
    keys = _keys(path)
    node = tree
    for k in keys[:-1]:
        if isinstance(node, list):
            node = node[k]
        else:
            node = node.setdefault(k, {})
    last = keys[-1]
    if isinstance(node, list):
        old = node[last] if -len(node) <= last < len(node) else _MISSING
        if value is _MISSING:
            if old is not _MISSING:
                node.pop(last)
        elif last == len(node):
            node.append(value)
        else:
            node[last] = value
        return old
    old = node.get(last, _MISSING)
    if value is _MISSING:
        node.pop(last, None)
    else:
        node[last] = value
    return old


class Store:
    def __init__(self, area, initial=None, schema=1, clock=time.monotonic):
        self.area, self.schema, self.clock = area, schema, clock
        self.tree = _plain(initial or {})
        self._undo, self._redo = [], []  # entries: {"text", "changes": [(path, old, new)], "time", "merge"}
        self._listeners = []
        self._batch = None
        self.saved_index = 0  # len(self._undo) at the last save: tells whether there is something unsaved

    # --- reading --------------------------------------------------------------
    def get(self, path, default=None):
        return get(self.tree, path, default)

    def subscribe(self, callback):
        """callback(paths: list[str]) after every change, undo and redo. Returns a function that unsubscribes."""
        self._listeners.append(callback)
        return lambda: self._listeners.remove(callback)

    def _emit(self, paths):
        for callback in list(self._listeners):
            callback(list(paths))

    # --- changing ---------------------------------------------------------------
    def set(self, path, value, text=None):
        """Change one value (one undo step named text, unless inside batch())."""
        value = _plain(value)
        if get(self.tree, path, _MISSING) == value:
            return
        keys = path.split(".")
        for i in range(1, len(keys)):  # missing parents: record the change at the first one, so undo removes it
            if get(self.tree, ".".join(keys[:i]), _MISSING) is _MISSING:
                for k in reversed(keys[i:]):
                    value = {k: value}
                path = ".".join(keys[:i])
                break
        old = _put(self.tree, path, value)
        self._record(path, old, value, text or path)

    def default(self, path, value):
        """Fill a missing value without an undo step (a control's starting value)."""
        if get(self.tree, path, _MISSING) is _MISSING:
            _put(self.tree, path, _plain(value))

    def delete(self, path, text=None):
        if get(self.tree, path, _MISSING) is _MISSING:
            return
        parent, _, last = path.rpartition(".")
        items = get(self.tree, parent) if parent else None
        if isinstance(items, list):  # removing a list item shifts the rest: record it as a change of the whole list
            self.set(parent, [v for i, v in enumerate(items) if i != int(last) % len(items)], text or path)
            return
        old = _put(self.tree, path, _MISSING)
        self._record(path, old, _MISSING, text or path)

    def _record(self, path, old, new, text):
        change = (path, _copy(old), _copy(new))
        if self._batch is not None:
            self._batch["changes"].append(change)
            return
        now = self.clock()
        last = self._undo[-1] if self._undo else None
        if last and last["merge"] == path and now - last["time"] < MERGE_SECONDS and len(self._undo) > self.saved_index:
            last["changes"][-1] = (path, last["changes"][-1][1], change[2])
            last["time"] = now
        else:
            self._undo.append({"text": text, "changes": [change], "time": now, "merge": path})
        self._redo.clear()
        self._emit([path])

    @contextmanager
    def batch(self, text):
        """Several changes as one undo step; nested batches join the outer one."""
        if self._batch is not None:
            yield
            return
        self._batch = {"text": text, "changes": [], "time": self.clock(), "merge": None}
        try:
            yield
        finally:
            entry, self._batch = self._batch, None
            if entry["changes"]:
                self._undo.append(entry)
                self._redo.clear()
                self._emit(sorted({p for p, _, _ in entry["changes"]}))

    # --- undo / redo --------------------------------------------------------------
    def can_undo(self):
        return bool(self._undo)

    def can_redo(self):
        return bool(self._redo)

    def undo_text(self):
        return self._undo[-1]["text"] if self._undo else ""

    def redo_text(self):
        return self._redo[-1]["text"] if self._redo else ""

    def undo(self):
        if not self._undo:
            return
        entry = self._undo.pop()
        for path, old, _ in reversed(entry["changes"]):
            _put(self.tree, path, _copy(old))
        entry["merge"] = None  # a redone step never merges with what follows
        self._redo.append(entry)
        self._emit(sorted({p for p, _, _ in entry["changes"]}))

    def redo(self):
        if not self._redo:
            return
        entry = self._redo.pop()
        for path, _, new in entry["changes"]:
            _put(self.tree, path, _copy(new))
        self._undo.append(entry)
        self._emit(sorted({p for p, _, _ in entry["changes"]}))

    def modified(self):
        """True when there are changes since the last to_json(saved=True)."""
        return len(self._undo) != self.saved_index

    # --- saving -------------------------------------------------------------------
    def to_json(self, saved=True):
        if saved:
            self.saved_index = len(self._undo)
        return json.dumps({"area": self.area, "schema": self.schema, "state": self.tree}, ensure_ascii=False)

    @classmethod
    def from_json(cls, text, area=None, schema=1, clock=time.monotonic):
        """A store from saved text, carried through the registered migrations up to `schema`. A state of another
        area or of a newer schema is refused (ValueError) rather than misread."""
        data = json.loads(text)
        found_area, found_schema, tree = data.get("area"), int(data.get("schema", 1)), data.get("state", {})
        if area is not None and found_area != area:
            raise ValueError(f"this session belongs to the {found_area} window, not to the {area} window")
        if found_schema > schema:
            raise ValueError("this session was saved by a newer version of the application: update it to open it")
        while found_schema < schema:
            step = MIGRATIONS.get((found_area, found_schema))
            if step is None:
                raise ValueError(f"no way to read a session of version {found_schema} of the {found_area} window")
            tree, found_schema = step(tree), found_schema + 1
        return cls(found_area, tree, schema=schema, clock=clock)
