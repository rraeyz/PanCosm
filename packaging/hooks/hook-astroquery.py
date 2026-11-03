# astroquery reads files next to its modules (CITATION on import, the SIMBAD field list, ...): ship them.
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

hiddenimports = collect_submodules("astroquery", filter=lambda name: ".tests" not in name)
datas = collect_data_files("astroquery", excludes=["**/tests/**"])
