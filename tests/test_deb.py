"""ARC-20: the .deb for Debian and Ubuntu, built from the program folder PyInstaller makes."""

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

BUILD = Path(__file__).resolve().parents[1] / "packaging" / "build.py"


@pytest.mark.skipif(not shutil.which("dpkg-deb") or sys.platform != "linux", reason="needs dpkg-deb")
def test_deb_installs_under_opt_with_a_command_and_a_menu_entry(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("pkgbuild_main", BUILD)
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)
    app, short = build.BRAND["app_id"], build.SHORT
    (tmp_path / "dist" / short).mkdir(parents=True)
    (tmp_path / "dist" / short / short).write_text("#!/bin/sh\n")
    monkeypatch.setattr(build, "OUT", tmp_path)
    monkeypatch.setattr(build, "DIST", tmp_path / "dist")
    deb = build.deb(f"[Desktop Entry]\nExec={short} %F\n")
    info = subprocess.run(["dpkg-deb", "--info", deb], capture_output=True, text=True, check=True).stdout
    files = subprocess.run(["dpkg-deb", "--contents", deb], capture_output=True, text=True, check=True).stdout
    assert f"Package: {app}" in info and f"Version: {build.VERSION}" in info
    assert f"./opt/{app}/{short}" in files and f"./usr/bin/{app} -> /opt/{app}/{short}" in files
    assert f"./usr/share/applications/{app}.desktop" in files
