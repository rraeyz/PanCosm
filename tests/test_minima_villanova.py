"""OC-4: the Villanova Kepler EB catalogue's ETV file read as minima records, offline from a recorded answer."""

import io
from pathlib import Path

import pytest

from astrowb.services import http, minima_villanova

DATA = Path(__file__).parent / "data" / "minima_services" / "villanova_kic7938468.etv.data"


def test_the_recorded_file_reads_as_primaries_and_secondaries():
    rows = minima_villanova.parse(DATA.read_text())
    assert len(rows) == 302  # 460 lines less the 158 whole-phase fits (eclipse 0); no (time, eclipse) twice
    first = rows[0]
    assert first["kind"] == "I" and first["standard_original"] == "BJD_TDB" and first["method"] == "space"
    assert first["time_original"] == pytest.approx(2454954.708895 + 0.002943, abs=1e-9)
    assert first["bjd_tdb"] == first["time_original"] and first["error"] == 0.0011 and not first["error_assumed"]
    assert rows[1]["kind"] == "II" and rows[1]["time_original"] == pytest.approx(2454958.326006 - 0.008, abs=1e-9)
    assert first["source"] == minima_villanova.SOURCE
    assert len({(r["time_original"], r["kind"]) for r in rows}) == len(rows)


def test_a_repeated_line_gives_one_record():
    text = "# BJD\tO-C (days)\tError (days)\tEclipse\n" + "100.5\t0.001\t0.0002\t1\n" * 2 + "100.5\t0.0\t0.0001\t0\n"
    assert len(minima_villanova.parse(text)) == 1


def test_a_500_answer_says_there_are_no_etvs(monkeypatch, tmp_path):
    monkeypatch.setattr("astrowb.services.cache.folder", lambda: tmp_path / "cache")

    def fail(url, params=None, **kw):
        raise http.HTTPError(url, 500, "Internal Server Error", {}, io.BytesIO())

    monkeypatch.setattr(http, "get", fail)
    with pytest.raises(ValueError, match="no eclipse timing variations for KIC 12644769 in the Villanova"):
        minima_villanova.fetch(12644769)


def test_the_answer_is_fetched_once(monkeypatch, tmp_path):
    monkeypatch.setattr("astrowb.services.cache.folder", lambda: tmp_path / "cache")
    calls = []

    def answer(url, params=None, **kw):
        calls.append(params)
        return DATA.read_bytes()

    monkeypatch.setattr(http, "get", answer)
    assert len(minima_villanova.minima(7938468)) == 302
    assert len(minima_villanova.minima(7938468)) == 302
    assert calls == [{"k": "7938468.00", "cadence": "lc", "data": "etv"}]
