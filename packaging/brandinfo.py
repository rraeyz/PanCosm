"""Brand + version for packaging scripts (read directly, so building needs no install)."""

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRAND_DIR = ROOT / "src" / "astrowb" / "resources" / "brand"
_raw = tomllib.loads((BRAND_DIR / "brand.toml").read_text(encoding="utf-8"))
BRAND = _raw["brand"] | _raw["stable"]
VERSION = re.search(r'__version__ = "(.+)"', (ROOT / "src" / "astrowb" / "__init__.py").read_text()).group(1)
ICON_PNG = BRAND_DIR / BRAND["icon"]
OUT = ROOT / "packaging" / "out"
