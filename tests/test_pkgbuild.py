"""ARC-20 item 3: the Arch PKGBUILD made from the release's AppImages."""

import hashlib
import importlib.util
import shutil
import subprocess
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "packaging" / "linux" / "pkgbuild.py"


def _tool():
    spec = importlib.util.spec_from_file_location("pkgbuild", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pkgbuild_names_each_appimage_with_its_checksum(tmp_path):
    tool = _tool()
    app, name, version = tool.BRAND["app_id"], tool.BRAND["short_name"], tool.VERSION
    image = tmp_path / f"{name}-{version}-linux-x86_64.AppImage"
    image.write_bytes(b"not really an AppImage")
    text = tool.write(tmp_path).read_text()
    assert f"pkgname={app}-bin" in text and "arch=(x86_64)" in text and "aarch64" not in text
    assert f"sha256sums_x86_64=('{hashlib.sha256(image.read_bytes()).hexdigest()}')" in text
    assert f"/releases/download/v{version}/{image.name}" in text
    if shutil.which("bash"):  # the file is valid shell: makepkg sources it
        run = subprocess.run(["bash", "-n", str(tmp_path / "PKGBUILD")], capture_output=True, text=True)
        assert run.returncode == 0, run.stderr
    with pytest.raises(SystemExit):
        tool.write(tmp_path / "empty")
