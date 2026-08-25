"""Frame-by-frame work on every core. Threads do not help there: astropy decompresses fpack / RICE frames holding
the interpreter lock (24 LCO frames: 2.34 s serial, 2.37 s on four threads), so the frames go to processes."""

import multiprocessing as mp
import os
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool


def workers():
    return max(1, os.cpu_count() or 1)


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
