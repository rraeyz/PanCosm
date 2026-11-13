# PyInstaller spec. Run through packaging/build.py. All names come from brand.toml.
import sys
from pathlib import Path

sys.path.insert(0, SPECPATH)
from brandinfo import BRAND, ICON_PNG, OUT, ROOT, VERSION  # noqa: E402

from PyInstaller.utils.hooks import collect_submodules  # noqa: E402

name = BRAND["short_name"]
icon = str(OUT / "icon.ico") if sys.platform == "win32" else str(ICON_PNG)

a = Analysis(
    [str(Path(SPECPATH) / "launcher.py")],
    pathex=[str(ROOT / "src")],
    datas=[
        (str(ROOT / "src" / "astrowb" / "resources"), "astrowb/resources"),
        (str(ROOT / "LICENSE"), "."),  # the GPL text travels with every copy
        (str(ROOT / "THIRD_PARTY.md"), "."),
    ],
    hookspath=[str(Path(SPECPATH) / "hooks")],
    hiddenimports=["astrowb.engine.builtin", "astrowb.ui.plot.view", "astrowb.ui.plot.publish"]  # plots: ARC-6
    + collect_submodules("alpaca")  # device classes load by name
    + [f"imagecodecs.{m}" for m in ("imagecodecs", "_jpeg2k", "_shared", "_shared_cython")]  # lazy codec imports
    # matplotlib finds its file writers by name when a figure is saved: PDF, SVG and EPS failed without these
    + [f"matplotlib.backends.backend_{b}" for b in ("pdf", "svg", "ps", "pgf", "agg")],
    excludes=["tkinter", "IPython", "pytest", "asdf", "asdf_astropy", "gwcs", "specutils", "specreduce", "ccdproc"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=name,
    console=False,
    icon=icon,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(exe, a.binaries, a.datas, name=name)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name=f"{BRAND['display_name']}.app",
        icon=icon,
        bundle_identifier=BRAND["bundle_id"],
        version=VERSION,
        info_plist={
            "CFBundleDisplayName": BRAND["display_name"],
            "CFBundleShortVersionString": VERSION,
            "NSHighResolutionCapable": True,
            "CFBundleDocumentTypes": [
                {"CFBundleTypeName": "Project", "CFBundleTypeExtensions": ["astroproj"], "CFBundleTypeRole": "Editor"},
                {"CFBundleTypeName": "FITS image", "CFBundleTypeExtensions": ["fits", "fit", "fts"], "CFBundleTypeRole": "Viewer"},
            ],
        },
    )
