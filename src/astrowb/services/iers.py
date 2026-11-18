"""IERS data downloads (plans/architecture.md ARC-14, ARC-20): one fixed https URL, certifi's trust store."""

from . import http


def fetch(url, timeout):
    import ssl

    import certifi

    ctx = ssl.create_default_context(cafile=certifi.where())
    return http.get(url, timeout=timeout, agent="Mozilla/5.0", context=ctx)
