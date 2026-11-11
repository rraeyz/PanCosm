"""User settings stored as JSON in the per-user config folder.

The folder is named after brand.app_id. After a rename, folders of previous app ids
are copied (never moved or deleted) to the new location on first start.
"""

import json
import os
import shutil
from pathlib import Path

import platformdirs

from .brand import BRAND

ENV_CONFIG_DIR = "ASTROWB_CONFIG_DIR"  # override, used by tests and portable installs
FILENAME = "settings.json"


def _dirs(app_id: str) -> list[Path]:
    return [
        platformdirs.user_config_path(app_id, appauthor=False),
        platformdirs.user_data_path(app_id, appauthor=False),
    ]


def migrate_previous(app_id: str = BRAND.app_id, previous: list[str] = BRAND.previous_app_ids) -> list[Path]:
    """Copy folders of old app ids to the new ones that do not exist yet. Returns the created folders."""
    created = []
    for old_id in previous:
        for old, new in zip(_dirs(old_id), _dirs(app_id), strict=True):
            if old.is_dir() and not new.exists():
                shutil.copytree(old, new)
                created.append(new)
    return created


def config_dir() -> Path:
    return Path(os.environ.get(ENV_CONFIG_DIR) or platformdirs.user_config_path(BRAND.app_id, appauthor=False))


class Settings:
    def __init__(self, directory: Path | None = None):
        self.path = (directory or config_dir()) / FILENAME
        try:
            self.values = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            self.values = {}

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        """Change one key. The file is read first: another window (another Settings object) may have changed
        other keys since this one was made, and writing a stale copy would undo them."""
        try:
            self.values = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError):
            pass
        self.values[key] = value
        self.save()

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.values, indent=2), encoding="utf-8")
        tmp.replace(self.path)  # atomic: a crash never leaves a half-written settings file
