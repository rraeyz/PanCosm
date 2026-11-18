"""GitHub's releases API (plans/architecture.md ARC-14): the newest published release of a repository."""

import json

from . import http


def latest(owner, repo, timeout=10):
    """The decoded JSON of the repository's latest release (OSError / ValueError on failure)."""
    return json.loads(
        http.get(
            f"https://api.github.com/repos/{owner}/{repo}/releases/latest",
            timeout=timeout,
            agent="update-check",
            headers={"Accept": "application/vnd.github+json"},
        )
    )
