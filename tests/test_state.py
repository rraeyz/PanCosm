"""ARC-5: the session store — undo / redo of any sequence of changes, merging of typing, batches, saving with
migrations."""

import json
import random

import numpy as np
import pytest

from astrowb.core import state
from astrowb.core.state import Store


class Clock:
    t = 0.0

    def __call__(self):
        return self.t


def initial():
    return {"apertures": {"r_ap": 6.0, "r_in": 12.0}, "stars": [{"role": "target", "x": 10.0}], "name": "NY Vir"}


def test_undo_all_returns_to_the_start_and_redo_all_to_the_end():
    """Property test: 300 random sequences of sets, deletes, batches and partial undos."""
    rng = random.Random(4)
    paths = ["apertures.r_ap", "apertures.r_in", "apertures.r_out", "stars.0.x", "stars.0.role", "name", "new.deep.key"]
    for _ in range(300):
        clock = Clock()
        s = Store("photometry", initial(), clock=clock)
        start = json.loads(json.dumps(s.tree))
        for _ in range(rng.randint(1, 25)):
            clock.t += rng.choice([0.1, 2.0])  # some changes merge, some do not
            op = rng.random()
            if op < 0.6:
                s.set(rng.choice(paths), rng.choice([1, 2.5, "x", None, [1, 2], {"a": 1}]))
            elif op < 0.7:
                s.delete(rng.choice(paths))
            elif op < 0.85:
                with s.batch("several"):
                    for _ in range(3):
                        s.set(rng.choice(paths), rng.random())
            else:
                for _ in range(rng.randint(0, 2)):
                    s.undo()
        end, ahead = json.loads(json.dumps(s.tree)), len(s._redo)  # steps undone at the end stay redoable
        while s.can_undo():
            s.undo()
        assert s.tree == start
        while s.can_redo():
            s.redo()
        for _ in range(ahead):
            s.undo()
        assert s.tree == end


def test_typing_merges_into_one_step_and_a_pause_starts_a_new_one():
    clock = Clock()
    s = Store("photometry", initial(), clock=clock)
    for v in (6.1, 6.2, 6.3):
        clock.t += 0.2
        s.set("apertures.r_ap", v, text="aperture radius")
    clock.t += 2
    s.set("apertures.r_ap", 7.0, text="aperture radius")
    s.undo()
    assert s.get("apertures.r_ap") == 6.3
    s.undo()
    assert s.get("apertures.r_ap") == 6.0 and not s.can_undo()
    assert s.redo_text() == "aperture radius"


def test_batch_is_one_step_and_listeners_hear_every_change():
    s = Store("photometry", initial())
    heard = []
    s.subscribe(heard.append)
    with s.batch("suggest comparison stars"):
        s.set("stars.1", {"role": "comparison", "x": 20.0})
        s.set("stars.2", {"role": "comparison", "x": 30.0})
    assert len(s.get("stars")) == 3 and heard == [["stars.1", "stars.2"]]
    assert s.undo_text() == "suggest comparison stars"
    s.undo()
    assert len(s.get("stars")) == 1 and heard[-1] == ["stars.1", "stars.2"]


def test_numpy_values_are_stored_as_plain_values():
    s = Store("spectroscopy", {})
    s.set("lines", np.array([[1.0, 4000.0], [2.0, 5000.0]]))
    s.set("n", np.int64(3))
    assert s.get("lines") == [[1.0, 4000.0], [2.0, 5000.0]] and type(s.get("n")) is int
    assert json.loads(s.to_json())["state"]["n"] == 3


def test_saving_migrations_and_refusals():
    @state.migration("testarea", 1)
    def radius_moved(tree):
        tree["apertures"] = {"r_ap": tree.pop("radius")}
        return tree

    old = json.dumps({"area": "testarea", "schema": 1, "state": {"radius": 5.0}})
    s = Store.from_json(old, area="testarea", schema=2)
    assert s.get("apertures.r_ap") == 5.0 and s.schema == 2
    with pytest.raises(ValueError, match="newer version"):
        Store.from_json(json.dumps({"area": "testarea", "schema": 3, "state": {}}), area="testarea", schema=2)
    with pytest.raises(ValueError, match="belongs to the"):
        Store.from_json(old, area="photometry")
    s.set("x", 1)
    assert s.modified()
    s.to_json()
    assert not s.modified()


def test_deleting_a_list_item_undoes_back_into_its_place():
    s = Store("photometry", {"stars": ["a", "b", "c"]})
    s.delete("stars.1")
    assert s.get("stars") == ["a", "c"]
    s.undo()
    assert s.get("stars") == ["a", "b", "c"]


def test_project_keeps_the_last_session(tmp_path):
    from astrowb.engine.project import Project

    s = Store("photometry", initial())
    with Project(tmp_path / "p.astroproj") as project:
        project.save_session("photometry", s.to_json())
        assert project.session("photometry") == s.to_json() and project.session("images") is None


def test_bound_controls_follow_the_store_both_ways(qapp):
    from PySide6.QtWidgets import QCheckBox, QDoubleSpinBox

    from astrowb.ui.kit.binding import bind

    s = Store("photometry", initial())
    spin, check = QDoubleSpinBox(), QCheckBox()
    bind(spin, s, "apertures.r_ap", "aperture radius")
    bind(check, s, "options.ensemble")
    assert spin.value() == 6.0 and s.get("options.ensemble") is False and not s.can_undo()
    spin.setValue(7.5)
    check.setChecked(True)
    assert s.get("apertures.r_ap") == 7.5 and s.get("options.ensemble") is True
    s.undo()
    s.undo()
    assert spin.value() == 6.0 and not check.isChecked()
