"""Product branding, read from resources/brand/brand.toml (the only file that names the product)."""

import tomllib
from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path

BRAND_DIR = Path(str(files("astrowb") / "resources" / "brand"))


@dataclass(frozen=True)
class Brand:
    display_name: str
    short_name: str
    organization: str
    app_id: str
    bundle_id: str
    windows_app_user_model_id: str
    homepage: str
    issues_url: str
    icon: str
    windows_installer_guid: str
    previous_app_ids: list[str] = field(default_factory=list)

    @property
    def icon_path(self) -> Path:
        return BRAND_DIR / self.icon


def load(path: Path = BRAND_DIR / "brand.toml") -> Brand:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return Brand(**data["brand"], **data["stable"])


BRAND = load()
