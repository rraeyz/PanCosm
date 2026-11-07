"""Build the installer for the current OS.  python packaging/build.py

Linux   -> packaging/out/<short>-<ver>-linux-<arch>.AppImage
Windows -> packaging/out/<short>-<ver>-windows-x64-setup.exe   (needs Inno Setup 6: iscc)
macOS   -> packaging/out/<short>-<ver>-macos-<arch>.dmg
"""

import os
import platform
import shutil
import stat
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from brandinfo import BRAND, ICON_PNG, OUT, ROOT, VERSION  # noqa: E402

HERE = Path(__file__).parent
DIST, WORK = OUT / "dist", OUT / "build"
SHORT = BRAND["short_name"]
ARCH = {"amd64": "x86_64", "x86_64": "x86_64", "arm64": "arm64", "aarch64": "aarch64"}[platform.machine().lower()]
APPIMAGETOOL_URL = f"https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-{ARCH}.AppImage"


def run(*cmd, **kw):
    print("+", " ".join(map(str, cmd)), flush=True)
    subprocess.run([str(c) for c in cmd], check=True, **kw)


def pyinstaller():
    OUT.mkdir(parents=True, exist_ok=True)
    run(sys.executable, ROOT / "tools" / "i18n.py")
    if sys.platform == "win32":
        from PIL import Image

        Image.open(ICON_PNG).save(OUT / "icon.ico", sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    run(
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--distpath",
        DIST,
        "--workpath",
        WORK,
        HERE / "app.spec",
    )


def linux():
    appdir = OUT / "AppDir"
    shutil.rmtree(appdir, ignore_errors=True)
    shutil.copytree(DIST / SHORT, appdir / "usr" / "lib" / SHORT)
    app_id = BRAND["app_id"]
    (appdir / "AppRun").write_text(
        f'#!/bin/sh\nHERE="$(dirname "$(readlink -f "$0")")"\nexec "$HERE/usr/lib/{SHORT}/{SHORT}" "$@"\n'
    )
    (appdir / "AppRun").chmod(0o755)
    desktop = (
        "[Desktop Entry]\nType=Application\n"
        f"Name={BRAND['display_name']}\nExec={SHORT} %F\nIcon={app_id}\n"
        "Categories=Science;Astronomy;Education;\nTerminal=false\n"
    )
    (appdir / f"{app_id}.desktop").write_text(desktop)
    shutil.copy(ICON_PNG, appdir / f"{app_id}.png")
    tool = OUT / "appimagetool"
    if not tool.exists():
        urllib.request.urlretrieve(APPIMAGETOOL_URL, tool)
        tool.chmod(tool.stat().st_mode | stat.S_IEXEC)
    target = OUT / f"{SHORT}-{VERSION}-linux-{ARCH}.AppImage"
    env = os.environ | {"ARCH": ARCH, "APPIMAGE_EXTRACT_AND_RUN": "1"}  # works without FUSE (CI, containers)
    run(tool, "--no-appstream", appdir, target, env=env)
    return target


def windows():
    iscc = shutil.which("iscc") or r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    base = f"{SHORT}-{VERSION}-windows-x64-setup"
    defines = {
        "AppGuid": BRAND["windows_installer_guid"],
        "AppName": BRAND["display_name"],
        "AppVersion": VERSION,
        "AppPublisher": BRAND["organization"],
        "AppURL": BRAND["homepage"],
        "SupportURL": BRAND["issues_url"],
        "ExeName": f"{SHORT}.exe",
        "AumId": BRAND["windows_app_user_model_id"],
        "SourceDir": DIST / SHORT,
        "OutputDir": OUT,
        "OutputBase": base,
        "IconFile": OUT / "icon.ico",
    }
    run(iscc, *[f"/D{k}={v}" for k, v in defines.items()], HERE / "windows" / "installer.iss")
    return OUT / f"{base}.exe"


def macos():
    app = DIST / f"{BRAND['display_name']}.app"
    run("codesign", "--force", "--deep", "--sign", "-", app)  # ad-hoc; real signing needs an Apple Developer ID
    target = OUT / f"{SHORT}-{VERSION}-macos-{ARCH}.dmg"
    stage = OUT / "dmg"
    shutil.rmtree(stage, ignore_errors=True)
    stage.mkdir()
    run("cp", "-R", app, stage)  # cp -R keeps the bundle's symlinks
    (stage / "Applications").symlink_to("/Applications")
    target.unlink(missing_ok=True)
    for attempt in range(5):  # "Resource busy" on CI runners now and then (the image is still being scanned)
        try:
            run("hdiutil", "create", "-volname", BRAND["display_name"], "-srcfolder", stage, "-ov", "-format", "UDZO",
                target)  # fmt: skip
            break
        except subprocess.CalledProcessError:
            if attempt == 4:
                raise
            time.sleep(10 * (attempt + 1))
    return target


if __name__ == "__main__":
    pyinstaller()
    result = {"linux": linux, "win32": windows, "darwin": macos}[sys.platform]()
    print(f"built {result}")
