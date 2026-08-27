"""Is there a GPU, does every GPU job give the CPU's result, and how fast is each on both?

    python tools/gpu_check.py      (from the source folder; the installed application: --benchmark)

Prints one line per finding as it is known (about a minute) and exits 0 when every GPU job works."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

if __name__ == "__main__":  # the jobs may start worker processes
    from astrowb.compute.check import report

    lines = []
    for line in report():
        print(line, flush=True)
        lines.append(line)
    sys.exit(0 if any(line.endswith("GPU jobs work.") and line.split()[0] == line.split()[2] for line in lines) else 1)
