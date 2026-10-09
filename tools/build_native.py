"""Build the compiled routines (native/, Rust) and put the module next to the package: python tools/build_native.py

Needs Rust (rustup: the version in native/rust-toolchain.toml is installed by itself). The program runs without
the module (every routine has a NumPy twin), only slower. The installers are built after this step, so the module
travels inside them (packaging/app.spec picks up src/astrowb/_native.*).
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "native"
PACKAGE = ROOT / "src" / "astrowb"


def main():
    env = {**os.environ, "PYO3_PYTHON": sys.executable}
    subprocess.run(["cargo", "build", "--release", "--locked"], cwd=NATIVE, env=env, check=True)
    release = NATIVE / "target" / "release"
    if sys.platform == "win32":
        built, target = release / "_native.dll", PACKAGE / "_native.pyd"
    elif sys.platform == "darwin":
        built, target = release / "lib_native.dylib", PACKAGE / "_native.abi3.so"
    else:
        built, target = release / "lib_native.so", PACKAGE / "_native.abi3.so"
    for old in PACKAGE.glob("_native.*"):
        old.unlink()
    shutil.copy2(built, target)
    print(f"compiled routines: {target.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
