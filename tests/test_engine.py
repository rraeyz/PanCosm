import time

import numpy as np
import pytest
from astropy.io import fits

from astrowb.engine import steps
from astrowb.engine.core import Engine
from astrowb.engine.project import Project
from astrowb.engine.tasks import Cancelled, TaskFailed, TaskQueue


# Task functions must live at module level so the spawned worker can import them.
def add(a, b, ctx):
    ctx.progress(0.5, "half")
    return a + b


def boom(ctx):
    raise ValueError("bad input")


def slow(ctx):
    for _ in range(200):
        ctx.check()
        time.sleep(0.05)
    return "finished"


def die(ctx):
    import os

    os._exit(3)  # a hard crash (out of memory, a library fault): no exception, the process is gone


def stubborn(ctx):
    time.sleep(60)  # ignores cancel


@pytest.fixture(scope="module")
def tq():
    q = TaskQueue(max_workers=2)
    yield q
    q.shutdown()


def test_result_and_progress(tq):
    seen = []
    t = tq.submit(add, 2, 3)
    t.add_callback(lambda task: seen.append(task.state))
    assert t.result(30) == 5
    assert t.state == "done" and t.progress == 1.0


def test_error_is_reported(tq):
    t = tq.submit(boom)
    with pytest.raises(TaskFailed, match="bad input"):
        t.result(30)


def test_cancel_cooperative(tq):
    t = tq.submit(slow)
    while t.state != "running":
        time.sleep(0.05)
    t.cancel()
    with pytest.raises(Cancelled):
        t.result(30)


def test_cancel_terminates_stubborn_worker(tq):
    t = tq.submit(stubborn)
    while t.state != "running":
        time.sleep(0.05)
    t.cancel()
    with pytest.raises(Cancelled):
        t.result(30)


def stubborn_with_a_child(path, ctx):
    import subprocess
    import sys

    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
    open(path, "w").write(str(child.pid))
    time.sleep(60)  # ignores cancel, as a worker running a pool of processes


@pytest.mark.skipif(not hasattr(__import__("os"), "killpg"), reason="process groups are POSIX")
def test_a_stopped_worker_takes_its_own_processes_with_it(tq, tmp_path):
    """A worker that started processes (a pool for the frames) and is stopped leaves none of them running: on macOS
    such orphans held the resource tracker's pipe and the program never ended (CI, 2026-11-09)."""
    import os

    pid_file = tmp_path / "child.pid"
    t = tq.submit(stubborn_with_a_child, str(pid_file))
    while not pid_file.exists() or not pid_file.read_text():
        time.sleep(0.05)
    child = int(pid_file.read_text())
    t.cancel()
    with pytest.raises(Cancelled):
        t.result(30)
    for _ in range(100):
        try:
            os.kill(child, 0)
        except ProcessLookupError:
            break
        try:  # a zombie of a process whose parent is gone is reaped by init; ours may need a wait
            os.waitpid(child, os.WNOHANG)
        except ChildProcessError:
            pass
        time.sleep(0.1)
    else:
        raise AssertionError("the worker's child process is still running")


def test_project_records_runs(tmp_path, fits_file, tq):
    with Project(tmp_path / "p.astroproj") as p:
        fid = p.add_file(fits_file, "light")
        assert p.add_file(fits_file, "light") == fid  # same path is not duplicated
        eng = Engine(p, tq)
        out = eng.run_chain(["fits.save_as"], {"source": str(fits_file), "destination": str(tmp_path / "out.fits")})
        assert fits.getheader(out["destination"])["OBJECT"] == "TEST"
        time.sleep(0.2)  # record callback runs on the monitor thread
        [run] = p.runs()
        assert run["status"] == "done" and run["environment"]["astropy"]
    with Project(tmp_path / "p.astroproj") as p:  # reopen: data persisted
        assert p.files()[0]["kind"] == "light" and len(p.runs()) == 1


def test_project_paths_are_relative(tmp_path, fits_file):
    with Project(tmp_path / "p.astroproj") as p:
        p.add_file(fits_file, "light")
        assert p.db.execute("SELECT path FROM files").fetchone()[0] == "frame.fits"


def test_missing_input_named_before_running():
    with pytest.raises(steps.MissingInput) as e:
        steps.check_chain(["fits.save_as"], {"source": "x.fits"})
    assert e.value.names == ["destination"]


def test_bad_extension(tmp_path):
    with pytest.raises(ValueError):
        Project(tmp_path / "p.db")


def test_spare_worker_takes_the_next_task_and_cancel_still_works():
    from astrowb.engine import tasks

    q = TaskQueue(max_workers=1)
    try:
        deadline = time.monotonic() + 30
        while q._spare is None and time.monotonic() < deadline:
            time.sleep(0.05)
        spare_pid = q._spare[0].pid
        t = q.submit(add, 2, 3)
        assert t.result(30) == 5
        assert q._running == {} and (q._spare is None or q._spare[0].pid != spare_pid)  # the spare ran it
        t2 = q.submit(slow)  # taken by the next spare
        while t2.state != "running":
            time.sleep(0.05)
        t2.cancel()
        with pytest.raises(Cancelled):
            t2.result(30)
        assert q._spare is None or q._spare[0].pid != spare_pid  # a spare is never reused
        assert tasks.SPARE_DELAY_S > 0
    finally:
        q.shutdown()


def test_steps_fail_fast_on_wrong_inputs(tmp_path):
    """A wrong folder or file is an error at once (no "0 frames", no download before the check)."""
    from astrowb.engine import builtin  # noqa: F401
    from astrowb.engine.steps import execute

    class Ctx:
        def progress(self, *a):
            pass

        def check(self):
            pass

    with pytest.raises(ValueError, match="folder not found"):
        execute("calibration.scan", {"folder": str(tmp_path / "nope")}, {}, Ctx())
    t = time.perf_counter()
    with pytest.raises(OSError):  # the spectrum is read before the template library is fetched
        execute(
            "spectroscopy.classify", {"spectrum": str(tmp_path / "x.fits"), "library": str(tmp_path / "l")}, {}, Ctx()
        )
    assert time.perf_counter() - t < 2
    with pytest.raises(ValueError, match="target's name"):
        execute("timeseries.mission_lc", {"target": " ", "folder": str(tmp_path)}, {}, Ctx())
    frame = tmp_path / "f.fits"
    fits.PrimaryHDU(np.zeros((40, 60), np.float32), fits.Header({"DATE-OBS": "2026-11-15T20:00:00"})).writeto(frame)
    for step_id in ("photometry.light_curve", "photometry.apertures", "photometry.suggest_comparisons"):
        with pytest.raises(ValueError, match="target position 5000, 5000 is outside the image"):
            execute(step_id, {"images": [str(frame)], "target_xy": [5000, 5000], "comps_xy": [[1, 1]]}, {}, Ctx())
    with pytest.raises(ValueError, match=r"comparison star 2 at 70, 3 is outside the image \(60 × 40 px\)"):
        execute(
            "photometry.light_curve",
            {"images": [str(frame)], "target_xy": [5, 5], "comps_xy": [[1, 1], [70, 3]]},
            {},
            Ctx(),
        )


def test_a_worker_that_dies_is_reported(tq):
    t = tq.submit(die)
    with pytest.raises(TaskFailed, match="exited"):
        t.result(30)
    assert tq.submit(add, 1, 1).result(30) == 2  # the queue goes on


def test_frames_on_every_core_from_inside_a_task_worker():
    """A task worker is a daemon process: pmap still starts its helper processes there and keeps the order."""
    import math

    from astrowb.engine.parallel import pmap
    from astrowb.engine.tasks import TaskQueue

    q = TaskQueue(max_workers=1)
    try:
        out = q.submit(pmap, math.sqrt, list(range(40))).result(timeout=120)
    finally:
        q.shutdown()
    assert out == [math.sqrt(i) for i in range(40)]


def test_task_timeline_in_the_log(tq, caplog):
    """ARC-17: every task's start and end, with how long it took, are in the log (app.log at run time)."""
    import logging

    with caplog.at_level(logging.INFO, logger="astrowb.engine.tasks"):
        t = tq.submit(add, 2, 3, name="adding")
        t.wait(60)
    lines = [r.getMessage() for r in caplog.records]
    assert any(f"task {t.id} adding running" in line for line in lines)
    assert any(f"task {t.id} adding done after" in line for line in lines)
