# photutils reads its own package metadata at import time, and its Cython modules import each
# other in ways PyInstaller cannot see
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

datas = copy_metadata("photutils") + collect_data_files("photutils", excludes=["**/tests/**"])
hiddenimports = collect_submodules("photutils", filter=lambda name: ".tests" not in name)
