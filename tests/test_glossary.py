"""ARC-18: astronomy terms keep their fixed Turkish translation (resources/i18n/glossary.toml)."""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "tools"))
import translation_review  # noqa: E402

TS = """<?xml version="1.0" encoding="utf-8"?><!DOCTYPE TS><TS version="2.1" language="tr_TR"><context><name>X</name>
<message><source>Radial velocities of the stars</source><translation>Yıldızların radyal hızları</translation></message>
<message><source>Plate solving the frame</source><translation>Kareyi gök konumuna oturt</translation></message>
<message><source>e.g. isnan(airmass)</source><translation>ör. isnan(airmass)</translation></message>
<message><source>The light curves</source><translation>Işık eğrileri</translation></message>
<message><source>Flattened stars</source><translation>Basık yıldızlar</translation></message>
</context></TS>"""


def test_every_turkish_translation_uses_the_glossary():
    assert translation_review.glossary_problems("tr") == []


def test_the_check_finds_a_drifted_term_and_leaves_code_and_other_words(tmp_path, monkeypatch):
    shutil.copy(translation_review.I18N / "glossary.toml", tmp_path)
    (tmp_path / "app_tr.ts").write_text(TS, encoding="utf-8")
    monkeypatch.setattr(translation_review, "I18N", tmp_path)
    found = {term for _, _, term, _ in translation_review.glossary_problems("tr")}
    assert found == {"radial velocit*", "plate solv*"}  # Işık eğrileri: I lower-cased the Turkish way


def test_turkish_buttons_are_imperatives():
    """UI-18: a button says "Ölç", never "Ölçmek"."""
    assert translation_review.infinitives("tr") == []
