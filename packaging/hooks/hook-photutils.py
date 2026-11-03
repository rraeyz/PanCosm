# photutils reads its own package metadata at import time, and its Cython modules import each
# other in ways PyInstaller cannot see. It also asks for the installed versions of scipy and friends
# (astropy.utils.minversion reads their metadata): without it photutils.background and .psf fail.
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

datas = copy_metadata("photutils") + collect_data_files("photutils", excludes=["**/tests/**"])
for dist in ("scipy", "numpy", "astropy", "matplotlib"):
    datas += copy_metadata(dist)
hiddenimports = collect_submodules("photutils", filter=lambda name: ".tests" not in name)
