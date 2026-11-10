# GPU jobs

Each job here has a CPU twin and is used only where it is faster (plans/architecture.md ARC-10).

Rules for every GPU job:

1. Float32 only for values (fluxes, counts, powers). Never for times or coordinates: a BJD in float32 is off by
   minutes. Shift times to a small zero point in float64 on the CPU first, or keep that part on the CPU.
2. Inputs larger than the adapter's limits (buffer size, workgroup counts) are cut into chunks; the result does not
   depend on the chunking.
3. Any failure (no adapter, out of memory, a driver error) falls back to the CPU twin and is said once per session in
   the status; it never stops the work.
4. Results equal the CPU twin within the tolerance written next to the job in `check.py`; the equality test runs in
   CI on the software driver (lavapipe) where available.
5. "Automatic" never picks the GPU for a size where Help → Check the GPU measured it slower.
6. A software adapter (the CPU pretending to be a GPU) is never chosen by "Automatic".

Help → Check the GPU… (or `--benchmark`) runs every job on both and saves `gpu-report.json` in the settings folder;
Report a problem adds it to the zip.
