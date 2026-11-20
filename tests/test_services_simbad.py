import numpy as np
from astropy.table import Table

from astrowb.planning import targets
from astrowb.services import simbad


def test_object_table_cached_and_parsed(monkeypatch):
    asked = []

    def fetch(server):
        asked.append(server)
        return Table({"RA": ["16 42 41.0"], "DEC": ["+52 41 25"], "V": np.ma.array([9.5])})

    monkeypatch.setattr(simbad, "object_table", lambda name, fetch=fetch: fetch("x"))
    t = targets._simbad("HAT-P-32")
    assert t.source == "SIMBAD" and abs(t.ra - 250.67) < 0.01 and t.vmag == 9.5 and asked == ["x"]


def test_http_get_encodes_params_and_sets_agent(monkeypatch):
    import urllib.request

    from astrowb.services import http

    seen = {}

    class Reply:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b"ok"

    def urlopen(req, timeout):
        seen.update(url=req.full_url, agent=req.get_header("User-agent"), timeout=timeout)
        return Reply()

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    assert http.get("https://x/y", {"a": 1}, 5, agent="Mozilla/5.0") == b"ok"
    assert seen == {"url": "https://x/y?a=1", "agent": "Mozilla/5.0", "timeout": 5}
    http.get("https://x/y")
    assert seen["url"] == "https://x/y" and seen["agent"] is None  # no header: Python's own


def test_vizier_region_first_table_or_empty(monkeypatch):
    import astroquery.vizier

    from astrowb import mirrors
    from astrowb.services import vizier

    class Vizier:
        def __init__(self, columns, row_limit, vizier_server):
            self.args = (columns, row_limit, vizier_server)

        def query_region(self, centre, radius, catalog):
            return [Table({"a": [1]}), "second"] if catalog == "full" else []

    monkeypatch.setattr(astroquery.vizier, "Vizier", Vizier)
    monkeypatch.setattr(mirrors, "cds", lambda kind, ask: ask("srv"))
    assert len(vizier.region(None, None, "full", ["*"], 5)) == 2
    assert len(vizier.region(None, None, "full", ["*"], 5, first=True)) == 1
    assert vizier.region(None, None, "none", ["*"], 5, first=True) == []
