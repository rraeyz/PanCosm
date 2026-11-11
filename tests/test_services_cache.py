"""ARC-14: answers are kept, age per service, serve when the network fails, and alone when working offline."""

import time

import pytest

from astrowb.services import cache


def test_answers_are_kept_and_reused(monkeypatch):
    calls = []

    def fetch():
        calls.append(1)
        return {"rows": [1, 2, 3]}

    assert cache.cached("vizier", ("cone", 1.0, 2.0), fetch) == {"rows": [1, 2, 3]}
    assert cache.cached("vizier", ("cone", 1.0, 2.0), fetch) == {"rows": [1, 2, 3]} and len(calls) == 1
    assert cache.last["vizier"][1] is True
    cache.cached("vizier", ("cone", 1.0, 2.5), fetch)
    assert len(calls) == 2 and cache.size()[0] == 2


def test_aged_answers_are_fetched_again_and_kept_when_the_network_fails(monkeypatch):
    cache.cached("ephemerides", "Algol", lambda: "old")
    monkeypatch.setattr(time, "time", lambda: 1e12)  # long after: the answer has aged
    assert cache.cached("ephemerides", "Algol", lambda: "new") == "new"
    monkeypatch.setattr(time, "time", lambda: 2e12)

    def down():
        raise OSError("network unreachable")

    assert cache.cached("ephemerides", "Algol", down) == "new"  # the older answer, not an error
    with pytest.raises(OSError):
        cache.cached("ephemerides", "Mira", down)  # nothing kept: the error


def test_not_found_is_an_answer_and_offline_uses_only_the_cache(monkeypatch):
    def missing():
        raise LookupError("not there")

    cache.cached("simbad", "Vega", lambda: "here")
    with pytest.raises(LookupError):
        cache.cached("simbad", "Nothing", missing)
    cache.set_offline(True)
    try:
        assert cache.cached("simbad", "Vega", lambda: pytest.fail("no network offline")) == "here"
        with pytest.raises(cache.OfflineError, match="not in the cache"):
            cache.cached("simbad", "Deneb", lambda: "x")
    finally:
        cache.set_offline(False)


def test_the_cache_stays_under_its_size(monkeypatch):
    monkeypatch.setattr(cache, "MAX_BYTES", 30_000)
    for i in range(10):
        cache.cached("hips2fits", f"image {i}", lambda: b"x" * 10_000)
    n, size = cache.size()
    assert size <= 30_000 and n < 10
    assert cache.cached("hips2fits", "image 9", lambda: pytest.fail("the newest stays")) == b"x" * 10_000
    cache.clear()
    assert cache.size() == (0, 0)


def test_the_internet_check_asks_the_network_not_the_cache():
    cache.cached("simbad", "Vega", lambda: 1)
    with cache.fresh():
        assert cache.cached("simbad", "Vega", lambda: 2) == 2  # asked again, and kept
        with pytest.raises(ConnectionError):  # a failing network is reported, not hidden by the old answer
            cache.cached("simbad", "Vega", lambda: (_ for _ in ()).throw(ConnectionError("down")))
    assert cache.cached("simbad", "Vega", lambda: 3) == 2
