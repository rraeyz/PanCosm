# pyvo (used by astroquery) reads data files next to its modules on import; without them astropy tries
# to download them from the internet and the import fails.
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

hiddenimports = collect_submodules("pyvo", filter=lambda name: ".tests" not in name)
datas = collect_data_files("pyvo", excludes=["**/tests/**"])
