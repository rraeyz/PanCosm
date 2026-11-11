"""An Arch Linux PKGBUILD (Arch, CachyOS, Manjaro) for the release's AppImages (plans/architecture.md ARC-20 item 3).

    python packaging/linux/pkgbuild.py out/   # reads out/*-linux-*.AppImage, writes out/PKGBUILD

The package is the "-bin" kind: it installs the released AppImage, extracted, under /opt, with a command in
/usr/bin and a menu entry; `makepkg -si` in the folder of the PKGBUILD builds and installs it. Names come from
brand.toml, so the file is made at release time rather than kept in the repository.
"""

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brandinfo import BRAND, VERSION  # noqa: E402

ARCHES = {"x86_64": "x86_64", "aarch64": "aarch64"}  # Arch name -> the AppImage's


def text(sums, version=VERSION, brand=BRAND):
    """The PKGBUILD for {arch: sha256} of the AppImages."""
    app, name = brand["app_id"], brand["short_name"]
    url = f"{brand['homepage']}/releases/download/v{version}/{name}-{version}-linux-{{arch}}.AppImage"
    arches = [a for a in ARCHES if a in sums]
    lines = [
        "# Made by packaging/linux/pkgbuild.py for this release; build and install with: makepkg -si",
        f"pkgname={app}-bin",
        f"pkgver={version.replace('-', '_')}",
        "pkgrel=1",
        f"pkgdesc='{brand['display_name']}: an astronomy workbench (calibration, photometry, spectroscopy, timing)'",
        f"arch=({' '.join(arches)})",
        f"url='{brand['homepage']}'",
        "license=('GPL-3.0-or-later')",
        f"provides=({app})",
        f"conflicts=({app})",
        "options=(!strip !debug)  # the bundled libraries are used as they were built",
    ]
    for a in arches:
        lines.append(f'source_{a}=("{url.format(arch=ARCHES[a])}")')
        lines.append(f"sha256sums_{a}=('{sums[a]}')")
    lines += [
        "",
        "prepare() {",
        "  chmod +x ./*.AppImage",
        "  ./*.AppImage --appimage-extract >/dev/null  # no FUSE needed",
        "}",
        "",
        "package() {",
        '  install -d "$pkgdir/opt" "$pkgdir/usr/bin"',
        f'  cp -a squashfs-root "$pkgdir/opt/{app}"',
        f'  chmod -R a+rX "$pkgdir/opt/{app}"',
        f'  ln -s /opt/{app}/AppRun "$pkgdir/usr/bin/{app}"',
        f'  install -Dm644 squashfs-root/{app}.png "$pkgdir/usr/share/icons/hicolor/512x512/apps/{app}.png"',
        f'  install -Dm644 /dev/stdin "$pkgdir/usr/share/applications/{app}.desktop" <<EOF',
        "[Desktop Entry]",
        "Type=Application",
        f"Name={brand['display_name']}",
        "Comment=Astronomy workbench",
        f"Exec=/opt/{app}/AppRun %F",
        f"Icon={app}",
        "Categories=Science;Astronomy;Education;",
        "Terminal=false",
        "EOF",
        "}",
    ]
    return "\n".join(lines) + "\n"


def write(folder):
    folder = Path(folder)
    sums = {}
    for arch, image_arch in ARCHES.items():
        found = sorted(folder.glob(f"*-linux-{image_arch}.AppImage"))
        if found:
            sums[arch] = hashlib.sha256(found[-1].read_bytes()).hexdigest()
    if not sums:
        raise SystemExit(f"no Linux AppImage in {folder}")
    out = folder / "PKGBUILD"
    out.write_text(text(sums), encoding="utf-8")
    return out


if __name__ == "__main__":
    print(write(sys.argv[1] if len(sys.argv) > 1 else "packaging/out"))
