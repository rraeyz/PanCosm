"""PLN-13: the observing log from the frames' headers — nights that do not split at midnight, spans, filters,
events caught whole or in part."""

from astropy.io import fits

from astrowb.planning import obslog


def header(when, target, filt="V", exptime=60.0, airmass=1.2):
    return fits.Header({"DATE-OBS": when, "EXPTIME": exptime, "OBJECT": target, "FILTER": filt, "AIRMASS": airmass,
                        "SITELONG": 30.3356})  # fmt: skip


def test_a_night_across_midnight_and_two_spans():
    items = []
    for i in range(30):  # NY Vir 21:00–00:29 UTC, V and R
        h, m = divmod(21 * 60 + 7 * i, 60)
        day = "2026-11-13" if h < 24 else "2026-11-14"
        items.append((f"n{i}.fits", header(f"{day}T{h % 24:02d}:{m:02d}:00", "NY Vir", "VR"[i % 2], 60.0,
                                           1.1 + 0.01 * i)))  # fmt: skip
    for i in range(10):  # after a two-hour pause, the same target again
        items.append((f"m{i}.fits", header(f"2026-11-14T02:{30 + 2 * i:02d}:00", "NY Vir")))
    items.append(("x.fits", fits.Header({"OBJECT": "no time"})))  # no time: left out
    rows = obslog.frames_from_headers(items)
    assert len(rows) == 40 and {r["night"] for r in rows} == {"2026-11-13"}  # one night, not split at 00:00 UTC
    log = obslog.night_log(rows)
    assert len(log) == 2 and log[0]["frames"] == 30 and log[0]["filters"] == ["R", "V"]
    assert log[0]["exposure_s"] == 1800 and log[0]["airmass"][0] == 1.1
    stats = obslog.statistics(log)
    spans = sum(line["end"] - line["start"] for line in log) * 24
    assert stats["nights"] == 1 and abs(stats["hours_per_target"]["NY Vir"] - spans) < 1e-9


def test_event_coverage():
    assert obslog.coverage(0.0, 10.0, 2.0, 5.0) == "whole"
    assert obslog.coverage(0.0, 3.0, 2.0, 5.0) == "ingress"
    assert obslog.coverage(3.0, 9.0, 2.0, 5.0) == "egress"
    assert obslog.coverage(2.5, 4.0, 2.0, 5.0) == "middle"
    assert obslog.coverage(6.0, 9.0, 2.0, 5.0) is None


def test_the_log_as_csv(tmp_path):
    rows = obslog.frames_from_headers([("a.fits", header("2026-11-13T20:00:00", "AI Dra"))])
    path = obslog.to_csv(obslog.night_log(rows), tmp_path / "log.csv")
    text = path.read_text(encoding="utf-8").splitlines()
    assert text[0].startswith("night,target")
    assert text[1].startswith("2026-11-13,AI Dra,2026-11-13 20:00:00,2026-11-13 20:01:00,V,1,60")
