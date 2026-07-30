"""Fail if a package installed in the (build) environment has a copyleft licence we must not bundle.

The application is GPL-3.0-or-later; keeping GPL / AGPL libraries out of the bundle keeps the owner free to
relicense later (another licence, a separate commercial licence): only permissive and LGPL libraries may ship
inside the app. Run in the clean build environment (CI does).
"""

import sys
from importlib.metadata import distributions

# astrowb is our own code; the rest are build tools, not shipped as library code
BUILD_ONLY = {"astrowb", "pyinstaller", "pyinstaller-hooks-contrib", "pip", "setuptools", "wheel"}
FORBIDDEN = ("AGPL", "GPL", "GNU General Public", "Affero", "SSPL", "EUPL")
ALLOWED_MARKERS = ("LGPL", "Lesser General Public", "GPL-2.0-or-later WITH Bootloader", "Library General Public")


def licence(dist) -> str:
    md = dist.metadata
    parts = [md.get("License-Expression") or ""]
    parts += [c.split("::")[-1].strip() for c in md.get_all("Classifier") or [] if c.startswith("License ::")]
    if not any(parts) and md.get("License"):
        parts.append(md.get("License").splitlines()[0][:80])
    if not any(parts):  # fall back to the first line of a bundled licence file
        for f in dist.files or []:
            if "licen" in str(f).lower() and f.name.upper().startswith(("LICEN", "COPYING")):
                text = (f.locate().read_text(errors="replace").strip().splitlines() or [""])[0]
                parts.append(text[:80])
                break
    return "; ".join(p for p in parts if p) or "UNKNOWN"


def main() -> int:
    bad, unknown = [], []
    for dist in sorted(distributions(), key=lambda d: d.metadata["Name"].lower()):
        name = dist.metadata["Name"].lower()
        lic = licence(dist)
        if name in BUILD_ONLY:
            continue
        if lic == "UNKNOWN":
            unknown.append(name)
        elif any(f in lic for f in FORBIDDEN) and not any(a in lic for a in ALLOWED_MARKERS):
            bad.append(f"{name}: {lic}")
    for name in unknown:
        print(f"warning: no licence metadata for {name} (check manually)")
    for line in bad:
        print(f"copyleft dependency: {line}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
