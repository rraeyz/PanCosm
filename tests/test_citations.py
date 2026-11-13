"""ARC-11 item 3: every key a method cites has its BibTeX entry; the short texts read as a paper writes them."""

from astrowb.core import citations


def test_every_cited_key_has_an_entry():
    import astrowb.photometry.psf  # noqa: F401  (modules with marked functions register them on import)
    import astrowb.timeseries.minima  # noqa: F401

    assert citations.USED, "no function is marked"
    missing = {k for keys in citations.USED.values() for k in keys} - set(citations.entries())
    assert not missing


def test_short_texts_and_bibtex():
    assert citations.short("kwee1956") == "Kwee & van Woerden (1956)"
    assert citations.short("winn2008") == "Winn et al. (2008)"
    assert citations.short("stetson1987") == "Stetson (1987)"
    assert citations.short("collins2017") == "Collins et al. (2017)"
    text = citations.bibtex(["kwee1956", "stetson1987", "kwee1956"])
    assert text.count("@ARTICLE") == 2 and text.startswith("@ARTICLE{kwee1956,")

    @citations.cites("eastman2010")
    def bjd():
        pass

    assert bjd.__cites__ == ("eastman2010",) and citations.USED[f"{__name__}.{bjd.__qualname__}"] == ("eastman2010",)
