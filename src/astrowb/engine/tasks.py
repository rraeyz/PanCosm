"""Task queue: every long job runs in its own worker process, with progress and cancel.

A worker process (not a thread) keeps the UI responsive, survives a crash in native
code, and can be terminated if it ignores a cancel request.

Starting a process and importing the science libraries takes 1-2 s, so one spare process is kept
ready with everything imported; a task takes it over and a new spare starts behind it. Every task still
runs in a process of its own.
"""

import itertools
import multiprocessing as mp
import os
import queue
import threading
import time
import traceback
from collections import deque

CANCEL_GRACE_S = 5.0  # a task that ignores cancel() is terminated after this
SPARE_DELAY_S = 2.0  # the first spare starts after this, so it does not compete with the window opening


class Cancelled(Exception):
    pass


class TaskFailed(Exception):
    pass


class Context:
    """Handed to the task function as ``ctx``: report progress, check for cancel."""

    def __init__(self, task_id, messages, cancel_event):
        self._id, self._q, self._cancel = task_id, messages, cancel_event

    def progress(self, fraction: float, message: str = ""):
        self._q.put((self._id, "progress", (float(fraction), message)))

    @property
    def cancelled(self) -> bool:
        return self._cancel.is_set()

    def check(self):
        """Raise Cancelled if cancel was requested. Call this inside long loops."""
        if self._cancel.is_set():
            raise Cancelled()


class Task:
    def __init__(self, task_id, name, cancel_event):
        self.id, self.name = task_id, name
        self.state = "queued"  # queued | running | done | failed | cancelled
        self.progress, self.message = 0.0, ""
        self.error = None
        self._result = None
        self._cancel = cancel_event
        self._cancel_time = None
        self._done = threading.Event()
        self._callbacks = []

    def add_callback(self, fn):
        """fn(task) is called on every update, from a background thread."""
        self._callbacks.append(fn)

    def cancel(self):
        if not self._done.is_set():
            self._cancel.set()
            self._cancel_time = time.monotonic()

    @property
    def finished(self) -> bool:
        return self._done.is_set()

    def wait(self, timeout=None) -> bool:
        return self._done.wait(timeout)

    def result(self, timeout=None):
        if not self._done.wait(timeout):
            raise TimeoutError(self.name)
        if self.state == "cancelled":
            raise Cancelled(self.name)
        if self.state == "failed":
            raise TaskFailed(self.error)
        return self._result

    def _update(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)
        if self.state in ("done", "failed", "cancelled"):
            self._done.set()
        for fn in self._callbacks:
            fn(self)


def _worker(task_id, fn, args, kwargs, messages, cancel_event):
    ctx = Context(task_id, messages, cancel_event)
    try:
        messages.put((task_id, "done", fn(*args, ctx=ctx, **kwargs)))
    except Cancelled:
        messages.put((task_id, "cancelled", None))
    except BaseException:
        messages.put((task_id, "failed", traceback.format_exc()))


def _spare(inbox, messages, cancel_event):
    """A ready worker: import the steps now, then wait for one task."""
    try:
        from . import steps

        steps.get("fits.save_as")  # loads the built-in steps and the plugins
    except BaseException:  # a broken plugin is reported when its task runs, not here
        pass
    try:
        from .. import compute

        compute.probe()  # whether there is a GPU, while nothing waits
    except BaseException:
        pass
    job = inbox.get()
    if job is not None:
        _worker(*job, messages, cancel_event)


def _plugin_signature():
    """Names and times of the plugin files: a spare that started before a change must not be used."""
    try:
        from .plugins import plugin_dir

        return sorted((e.name, e.stat().st_mtime_ns) for e in os.scandir(plugin_dir()))
    except OSError:
        return []


class TaskQueue:
    def __init__(self, max_workers: int | None = None):
        self._mp = mp.get_context("spawn")  # same behaviour on Linux, Windows and macOS
        self._max = max_workers or max(1, (mp.cpu_count() or 2) - 1)
        self._messages = self._mp.Queue()
        self._ids = itertools.count(1)
        self._pending = deque()
        self._running = {}  # task_id -> (task, process)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._spare = None  # (process, inbox, cancel event, plugin signature)
        self._spare_after = time.monotonic() + SPARE_DELAY_S
        self._monitor = threading.Thread(target=self._loop, name="task-monitor", daemon=True)
        self._monitor.start()

    def submit(self, fn, *args, name: str | None = None, **kwargs) -> Task:
        """Run fn(*args, ctx=Context, **kwargs) in a worker. fn and arguments must be picklable."""
        task = Task(next(self._ids), name or getattr(fn, "__name__", "task"), self._mp.Event())
        with self._lock:
            self._pending.append((task, fn, args, kwargs))
        return task

    def shutdown(self, timeout: float = 10.0):
        with self._lock:
            for task, *_ in self._pending:
                task._update(state="cancelled")
            self._pending.clear()
            running = list(self._running.values())
        for task, _ in running:
            task.cancel()
        self._drop_spare()
        deadline = time.monotonic() + timeout
        for _, proc in running:
            proc.join(max(0.0, deadline - time.monotonic()))
            if proc.is_alive():
                proc.terminate()
        self._stop.set()
        self._monitor.join(2)

    def _start_ready(self):
        with self._lock:
            while self._pending and len(self._running) < self._max:
                task, fn, args, kwargs = self._pending.popleft()
                if task._cancel.is_set():
                    task._update(state="cancelled")
                    continue
                spare = self._take_spare()
                if spare:
                    proc, inbox, event, _ = spare
                    old, task._cancel = task._cancel, event
                    if old.is_set():  # cancelled while being handed over
                        event.set()
                    inbox.put((task.id, fn, args, kwargs))
                else:
                    proc = self._mp.Process(
                        target=_worker, args=(task.id, fn, args, kwargs, self._messages, task._cancel), daemon=True
                    )
                    proc.start()
                self._running[task.id] = (task, proc)
                task._update(state="running")
            if self._spare is None and time.monotonic() > self._spare_after and not self._stop.is_set():
                inbox, event = self._mp.SimpleQueue(), self._mp.Event()
                proc = self._mp.Process(target=_spare, args=(inbox, self._messages, event), daemon=True)
                proc.keep = (inbox, event)  # the child unpickles them after start(): they must outlive it here
                proc.start()
                self._spare = (proc, inbox, event, _plugin_signature())

    def _take_spare(self):
        spare, self._spare = self._spare, None
        if spare and spare[0].is_alive() and spare[3] == _plugin_signature():
            return spare
        if spare:
            self._end_spare(spare)
        return None

    def _drop_spare(self):
        with self._lock:
            spare, self._spare = self._spare, None
        if spare:
            self._end_spare(spare)

    @staticmethod
    def _end_spare(spare):
        proc, inbox, *_ = spare
        if proc.is_alive():
            proc.terminate()  # idle: nothing to lose
        proc.join(1)

    def _finish(self, task_id, state, payload):
        with self._lock:
            task, proc = self._running.pop(task_id, (None, None))
        if task is None:
            return
        proc.join(1)
        if state == "done":
            task._update(state="done", progress=1.0, _result=payload)
        elif state == "failed":
            task._update(state="failed", error=payload)
        else:
            task._update(state="cancelled")

    def _loop(self):
        while not self._stop.is_set():
            self._start_ready()
            with self._lock:
                dead = [tid for tid, (_, p) in self._running.items() if not p.is_alive()]
            try:  # drain after collecting dead workers, so their last message is not missed
                while True:
                    tid, kind, payload = self._messages.get(timeout=0.1)
                    if kind == "progress":
                        with self._lock:
                            entry = self._running.get(tid)
                        if entry:
                            entry[0]._update(progress=payload[0], message=payload[1])
                    else:
                        self._finish(tid, kind, payload)
            except queue.Empty:
                pass
            for tid in dead:
                with self._lock:
                    entry = self._running.get(tid)
                if entry:
                    task, proc = entry
                    state = "cancelled" if task._cancel.is_set() else "failed"
                    self._finish(tid, state, f"worker exited with code {proc.exitcode}")
            now = time.monotonic()
            with self._lock:
                stuck = [
                    p for t, p in self._running.values() if t._cancel_time and now - t._cancel_time > CANCEL_GRACE_S
                ]
            for proc in stuck:
                proc.terminate()  # reported as cancelled on the next pass
