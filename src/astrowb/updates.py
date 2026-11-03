"""Is there a newer release? Asks GitHub's releases API for the repository in brand.toml (homepage).

Only when the user asks (Help menu): the application never calls home on its own.
"""

import json
import re
import urllib.request

from . import __version__
from .brand import BRAND


def version_tuple(text):
    """'v1.10.2' -> (1, 10, 2); anything after the numbers (rc, dev) is ignored."""
    return tuple(int(n) for n in re.findall(r"\d+", str(text).split("-")[0])[:3])


def latest_release(timeout=10):
    """{"version", "url", "notes"} of the newest published release, or raise OSError / ValueError."""
    match = re.match(r"https://github\.com/([^/]+)/([^/]+?)/?$", BRAND.homepage)
    if not match:
        raise ValueError("no GitHub repository configured for update checks")
    req = urllib.request.Request(
        f"https://api.github.com/repos/{match[1]}/{match[2]}/releases/latest",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "update-check"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read())
    return {"version": data["tag_name"].lstrip("v"), "url": data["html_url"], "notes": data.get("body") or ""}


def check(fetch=latest_release, current=__version__):
    """(newer release or None, error text or None)."""
    try:
        rel = fetch()
    except (OSError, ValueError, KeyError) as e:
        return None, str(e)
    return (rel if version_tuple(rel["version"]) > version_tuple(current) else None), None
