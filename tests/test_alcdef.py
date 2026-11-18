"""ALCDEF 2.3.0 export (photometry/reports/alcdef.py): every required keyword, the DATA lines, the cross-checks."""

import pytest

from astrowb.photometry.reports import alcdef

REQUIRED = (
    "OBJECTNUMBER",
    "OBJECTNAME",
    "SESSIONDATE",
    "SESSIONTIME",
    "CONTACTNAME",
    "CONTACTINFO",
    "OBSERVERS",
    "FILTER",
    "MAGBAND",
    "DIFFERMAGS",
    "STANDARD",
    "LTCAPP",
    "LTCTYPE",
    "REDUCEDMAGS",
    "DELIMITER",
)


def session(**kw):
    s = {
        "jd": [2460000.50000, 2460000.51000, 2460000.52000],
        "mag": [18.3185, 18.368, 18.3],
        "mag_err": [0.055, 0.052, 0.05],
        "object_number": 18736,
        "object_name": "1998 NU",
        "contact_name": "A. Observer",
        "contact_info": "[a@b.org] Town",
        "observers": "A. Observer",
        "filter": "C",
        "magband": "V",
        "differmags": False,
        "standard": "INTERNAL",
        "ltcapp": "NONE",
        "reducedmags": "NONE",
        "lat": 34.27247,
        "lon": -116.38483,
        "facility": "Home",
        "ra": 108.725,
        "dec": 25.6667,
        "phase": 28.51,
    }
    return s | kw


def read(tmp_path, **kw):
    p = tmp_path / "a.txt"
    alcdef.write(p, session(**kw))
    raw = p.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf") and b"\r" not in raw
    return raw.decode().split("\n")[:-1]


def test_block_layout_and_required_keywords(tmp_path):
    ls = read(tmp_path)
    assert ls[0] == "STARTMETADATA" and ls[-1] == "ENDDATA"
    meta = ls[1 : ls.index("ENDMETADATA")]
    keys = [m.partition("=")[0] for m in meta]
    assert all(k in keys for k in REQUIRED) and all("=" in m for m in meta)
    d = dict(m.partition("=")[::2] for m in meta)
    assert d["SESSIONDATE"] == "2023-02-25" and d["SESSIONTIME"] == "00:14:24"  # JD 2460000.5 is 2023-02-25 0h UT
    assert (d["OBJECTRA"], d["OBJECTDEC"], d["OBSLATITUDE"], d["OBSLONGITUDE"]) == (
        "07:14.9",
        "+25 40",
        "+34.27247",
        "-116.38483",
    )
    assert (d["LTCTYPE"], d["DELIMITER"], d["SUBMITPDS"], d["REVISEDDATA"]) == ("NONE", "PIPE", "FALSE", "FALSE")
    assert "DIFFZEROMAG" not in d and "LTCDAYS" not in d and "UCORMAG" not in d


def test_data_lines(tmp_path):
    ls = read(tmp_path)
    data = ls[ls.index("ENDMETADATA") + 1 : -1]
    assert data == [
        "DATA=2460000.500000|+18.319|+0.055",
        "DATA=2460000.510000|+18.368|+0.052",
        "DATA=2460000.520000|+18.300|+0.050",
    ]
    assert read(tmp_path, mag_err=None)[-2] == "DATA=2460000.520000|+18.300"


@pytest.mark.parametrize(
    "missing",
    [
        "object_number",
        "object_name",
        "contact_name",
        "contact_info",
        "observers",
        "filter",
        "magband",
        "standard",
        "ltcapp",
        "reducedmags",
    ],
)
def test_missing_required_value_is_named(tmp_path, missing):
    s = session()
    del s[missing]
    kw = {
        "object_number": "OBJECTNUMBER",
        "object_name": "OBJECTNAME",
        "contact_name": "CONTACTNAME",
        "contact_info": "CONTACTINFO",
        "observers": "OBSERVERS",
        "filter": "FILTER",
        "magband": "MAGBAND",
        "standard": "STANDARD",
        "ltcapp": "LTCAPP",
        "reducedmags": "REDUCEDMAGS",
    }[missing]
    with pytest.raises(ValueError, match=kw):
        alcdef.write(tmp_path / "x.txt", s)
    assert not (tmp_path / "x.txt").exists()


def test_cross_checks(tmp_path):
    for bad in (
        {"ltcapp": "AVERAGE"},
        {"ltcapp": "AVERAGE", "ltcdays": 0},
        {"reducedmags": "AVERAGE"},
        {"differmags": True},
        {"standard": "NONE"},
        {"filter": "X"},
        {"jd": [1.0, 2.0], "mag": [1.0, 2.0], "mag_err": None},
        {"jd": [2460000.5], "mag": [1.0], "mag_err": None},
        {"mag": [1.0, float("nan"), 2.0]},
    ):
        with pytest.raises(ValueError):
            alcdef.write(tmp_path / "x.txt", session(**bad))
    ls = read(
        tmp_path,
        ltcapp="AVERAGE",
        ltcdays=-0.01099,
        reducedmags="AVERAGE",
        ucormag=-3.5,
        differmags=True,
        diffzeromag=25.0,
    )
    assert {
        "LTCAPP=AVERAGE",
        "LTCTYPE=LIGHTTIME",
        "LTCDAYS=-0.010990",
        "REDUCEDMAGS=AVERAGE",
        "UCORMAG=-3.500",
        "DIFFZEROMAG=+25.000",
    } <= set(ls)
    assert "DIFFZEROMAG" not in "".join(read(tmp_path, differmags=True, standard="NONE"))


def test_profile_fields():
    p = {
        "observer": {"name": "A. Observer", "observers": "", "mpc_code": "U82"},
        "site": {"name": "", "lat": 39.9, "lon": 32.8},
    }
    assert alcdef.profile_fields(p) == {"contact_name": "A. Observer", "mpc_code": "U82"}
    p["site"]["name"] = "Home"
    assert alcdef.profile_fields(p)["lat"] == 39.9
