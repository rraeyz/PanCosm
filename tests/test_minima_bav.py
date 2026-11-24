"""OC-4: a BAV LkDB list read as minima records. The LkDB's terms forbid passing its data on, so the text here is
synthetic, written in the documented layout (plans/oc.md OC-4); no recorded answer is kept."""

import pytest

from astrowb.services import http, minima_bav

HEAD = "# Star: XX Tst   GCVS-No. 999999\r\n# Elements: GCVS 2450000.1000 + 1.0000000 * E\r\n"
COLUMNS = "Minimum [HJD]\tMinimum [UT]\tEpoch\t(O-C) [d]\tPhotom.\tFilt.\tObserver\tSource\r\n"
ROWS = (
    "2450010.1012\t1995-10-20 14:25\t10\t0.0012\tC\tV\tMüller, J.\tBAVM 244 (=IBVS 6196)\r\n"
    "2450020.6005\t1995-10-31 02:24\t20.5\t0.0005\tE\t\tGöß, K.\tBBSAG 99\r\n"
    "2450030.0990\t1995-11-09 14:22\t30\t-0.0010\tV\t\tSøren\t\r\n"
    "2450040.1000\t1995-11-19 14:24\t40\t0.0000\tK\t\t\tLkDB\r\n"
)
TEXT = HEAD + COLUMNS + ROWS + "# Filt.: V = Johnson V\r\n"


def test_the_list_reads_as_primaries_and_secondaries():
    rows = minima_bav.parse(TEXT, "XX  Tst")
    assert [r["kind"] for r in rows] == ["I", "II", "I", "I"]
    assert [r["method"] for r in rows] == ["ccd", "pe", "vis", "unknown"]
    first = rows[0]
    assert first["time_original"] == 2450010.1012 and first["standard_original"] == "HJD unknown"
    assert first["error_assumed"] and first["error"] == 0.0005  # no error column: the method's default
    assert first["filter"] == "V" and first["observer"] == "Müller, J."
    assert first["source"] == "BAVM 244 (=IBVS 6196); BAV LkDB" and rows[2]["source"] == "BAV LkDB"
    assert rows[1]["observer"] == "Göß, K."


def test_a_list_for_another_star_is_refused():
    with pytest.raises(ValueError, match="the BAV answer was for another star"):
        minima_bav.parse(TEXT, "X Tst")  # "XX Tst" does not name X Tst


def test_the_form_is_posted_once_and_read_as_latin1(monkeypatch, tmp_path):
    monkeypatch.setattr("astrowb.services.cache.folder", lambda: tmp_path / "cache")
    calls = []

    def answer(url, form, **kw):
        calls.append(form)
        return TEXT.encode("latin-1")

    monkeypatch.setattr(http, "post", answer)
    assert minima_bav.minima("XX Tst")[0]["observer"] == "Müller, J."
    assert len(minima_bav.minima("XX Tst")) == 4
    assert len(calls) == 1
    assert calls[0]["kenn"] == "liste_min_text" and calls[0]["stern"] == "XX Tst" and calls[0]["quelle"] == "GCVS"


def test_another_stars_answer_is_not_cached(monkeypatch, tmp_path):
    monkeypatch.setattr("astrowb.services.cache.folder", lambda: tmp_path / "cache")
    answers = [TEXT.replace("XX Tst", "YY Tst"), TEXT]
    monkeypatch.setattr(http, "post", lambda url, form, **kw: answers.pop(0).encode("latin-1"))
    with pytest.raises(ValueError, match="another star"):
        minima_bav.fetch("XX Tst")
    assert len(minima_bav.minima("XX Tst")) == 4
