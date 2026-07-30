# Overrides the contrib hook: skip astropy's test modules (they break collection when pytest
# is installed and add ~40 MB).
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata


def _keep(name):
    # wcsaxes needs matplotlib, which is not shipped yet
    return ".tests" not in name and not name.endswith(".conftest") and "wcsaxes" not in name


hiddenimports = collect_submodules("astropy", filter=_keep)
datas = (
    collect_data_files("astropy", excludes=["**/tests/**"])
    # astropy reads its generated parser tables (*tab.py) as text at runtime
    + collect_data_files("astropy", include_py_files=True, includes=["**/*parsetab.py", "**/*lextab.py"])
    + collect_data_files("astropy_iers_data")
    + copy_metadata("astropy")
)
