from astrowb.photometry.mpc80 import mpc80_lines, pack_designation

ROW = {
    "time": "2026-11-20T03:04:05.678Z",
    "ra": 15.0 * (1 + 2 / 60 + 3.4567 / 3600),
    "dec": -(5 + 6 / 60 + 7.896 / 3600),
}


def test_line_fields_at_their_columns():
    (ln,) = mpc80_lines([ROW | {"mag": 18.24}], "2024 AB1", "a84", "V")
    assert len(ln) == 80
    assert ln[0:12] == "     K24A01B" and ln[13] == " " and ln[14] == "C"
    assert ln[15:32] == "2026 11 20.127843"  # 11045.678 s / 86400 = 0.12784350 -> 0.127843
    assert ln[32:44] == "01 02 03.457" and ln[44:56] == "-05 06 07.90"
    assert ln[65:70] == " 18.2" and ln[70] == "V" and ln[77:80] == "A84"


def test_blank_code_and_magnitude_and_numbered():
    (ln,) = mpc80_lines([ROW], "433")
    assert len(ln) == 80 and ln[:12] == "00433       " and ln[65:71] == " " * 6 and ln[77:] == "   "


def test_day_fraction_carry_and_ra_wrap():
    (ln,) = mpc80_lines([{"time": "2026-12-31T23:59:59.9999999", "ra": 359.99999999, "dec": 0.0}], "X1")
    assert ln[15:32] == "2027 01 01.000000" and ln[32:44] == "00 00 00.000" and ln[44:56] == "+00 00 00.00"


def test_pack():
    assert pack_designation("1995 XA") == "     J95X00A"
    assert pack_designation("2026 VA12") == "     K26V12A"
