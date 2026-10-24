"""Install the built installer like a user would, then run the installed app's --smoke-test.

Phase 0 gate check, run by CI on each OS after packaging/build.py.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from brandinfo import BRAND, OUT  # noqa: E402

SHORT, NAME = BRAND["short_name"], BRAND["display_name"]


def one(pattern):
    [found] = list(OUT.glob(pattern))
    return found


def install() -> Path:
    """Return the installed executable."""
    if sys.platform == "win32":
        target = Path(tempfile.mkdtemp()) / "installed"
        subprocess.run(
            [one("*-setup.exe"), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/CURRENTUSER", f"/DIR={target}"], check=True
        )
        return target / f"{SHORT}.exe"
    if sys.platform == "darwin":
        mount = Path(tempfile.mkdtemp())
        subprocess.run(["hdiutil", "attach", "-nobrowse", "-mountpoint", mount, one("*.dmg")], check=True)
        apps = Path.home() / "Applications"
        apps.mkdir(exist_ok=True)
        shutil.rmtree(apps / f"{NAME}.app", ignore_errors=True)
        subprocess.run(["cp", "-R", mount / f"{NAME}.app", apps], check=True)
        subprocess.run(["hdiutil", "detach", mount], check=True)
        return apps / f"{NAME}.app" / "Contents" / "MacOS" / SHORT
    if os.environ.get("SMOKE_DEB"):  # Debian / Ubuntu (as root in CI's containers): the .deb, through apt
        subprocess.run(["apt-get", "install", "-y", str(one("*-linux-amd64.deb").resolve())], check=True)
        return Path("/usr/bin") / BRAND["app_id"]
    image = one("*.AppImage")
    image.chmod(0o755)
    return image


def main():
    exe = install()
    workdir = Path(tempfile.mkdtemp()) / "smoke"
    env = os.environ | {"QT_QPA_PLATFORM": "offscreen", "APPIMAGE_EXTRACT_AND_RUN": "1"}
    proc = subprocess.run([exe, "--smoke-test", workdir], env=env, timeout=600)
    result = (workdir / "smoke-result.txt").read_text() if (workdir / "smoke-result.txt").exists() else "no result"
    print(result)
    if proc.returncode != 0 or result.strip() != "OK":
        sys.exit(f"smoke test failed (exit code {proc.returncode})")
    print(f"installed {exe} — smoke test OK")


if __name__ == "__main__":
    main()
