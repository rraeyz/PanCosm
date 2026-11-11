"""UI-17: the splash shows at once with the program's name while the main window loads; a check's report is printed
and saved beside the settings."""


def test_splash_and_report(qapp, tmp_path, capsys):
    from astrowb.__main__ import _report, _splash
    from astrowb.brand import BRAND

    splash = _splash(qapp)
    assert splash.isVisible() and BRAND.display_name in splash.message()
    splash.close()
    _report("all fine", tmp_path / "sub" / "check.txt", "--check-online")
    assert (tmp_path / "sub" / "check.txt").read_text(encoding="utf-8") == "all fine\n"
    assert "all fine" in capsys.readouterr().out
