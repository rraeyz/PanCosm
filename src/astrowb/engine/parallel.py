"""Frame-by-frame work on every core. Threads do not help there: astropy decompresses fpack / RICE frames holding
the interpreter lock (24 LCO frames: 2.34 s serial, 2.37 s on four threads), so the frames go to processes."""

import multiprocessing as mp
import os
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool


def workers():
    return max(1, os.cpu_count() or 1)


def available_memory():
    """Bytes of memory free for new work now (Linux MemAvailable, Windows ullAvailPhys, macOS free + inactive +
    speculative pages), or None when it cannot be read."""
    import subprocess
    import sys

    try:
        if sys.platform.startswith("linux"):
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemAvailable:"):
                        return int(line.split()[1]) * 1024
        elif sys.platform == "win32":
            import ctypes

            class Status(ctypes.Structure):
                _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
                    (n, ctypes.c_ulonglong)
                    for n in ("total", "avail", "total_page", "avail_page", "total_virtual", "avail_virtual", "ext")
                ]

            st = Status()
            st.length = ctypes.sizeof(Status)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st)):
                return int(st.avail)
        elif sys.platform == "darwin":
            import re

            out = subprocess.run(["vm_stat"], capture_output=True, text=True, timeout=5).stdout
            size = int(re.search(r"page size of (\d+)", out).group(1))
            pages = sum(int(m) for m in re.findall(r"Pages (?:free|inactive|speculative):\s+(\d+)", out))
            return pages * size
    except (OSError, ValueError, AttributeError, subprocess.SubprocessError):
        return None
    return None


def pmap(fn, items, ctx=None, label="", min_items=8):
    """[fn(x) for x in items], in order, on separate processes (spawn: the same on Windows, macOS and Linux). fn must
    be a module-level function. Few items, or one core, run here: starting processes costs about a second. ctx: the
    step's context, for progress and cancel (the pending items are dropped)."""
    items = list(items)
    n = min(workers(), len(items))
    if n <= 1 or len(items) < min_items:
        out = []
        for i, x in enumerate(items):
            if ctx:
                ctx.check()
                ctx.progress(i / len(items), label)
            out.append(fn(x))
        return out
    # a task worker is a daemon process, and those may not start children; these end with the pool below
    mp.current_process().daemon = False
    out = []
    try:
        with ProcessPoolExecutor(n, mp_context=mp.get_context("spawn")) as pool:
            try:
                for i, r in enumerate(pool.map(fn, items, chunksize=max(1, len(items) // (n * 8)))):
                    if ctx:
                        ctx.check()
                        ctx.progress(i / len(items), label)
                    out.append(r)
            except BaseException:
                pool.shutdown(wait=False, cancel_futures=True)
                raise
    except BrokenProcessPool:  # a script without `if __name__ == "__main__":` cannot start processes: one core then
        return pmap(fn, items, ctx, label, min_items=len(items) + 1)
    return out
