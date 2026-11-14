"""ARC-11 item 3: every key a method cites has its BibTeX entry; the short texts read as a paper writes them."""

from astrowb.core import citations


def test_every_cited_key_has_an_entry():
    import astrowb.photometry.psf  # noqa: F401  (modules with marked functions register them on import)
    import astrowb.photometry.systematics  # noqa: F401
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


def test_the_methods_text_cites_what_was_used():
    """The paragraph for a paper names the ensemble with missing stars, the airmass formula, scintillation and β."""
    from astrowb.photometry.reports.methods import methods

    lc = {"time": [1.0, 2.0, 3.0], "comp_flux": [[1.0, 2.0]] * 3, "airmass": [1.1, 1.2, 1.3], "scintillation": True,
          "aperture_m": 0.4, "partial": {"f2.fits": [2]}}  # fmt: skip
    fit = {"values": {"tc": 2.0, "k": 0.1}, "errors": {"tc": 1e-4}, "derived": {"depth_ppt": 10.0}, "beta": 1.4,
           "red_noise_scale": 1.4}  # fmt: skip
    text, bib = methods(lc, fit)
    for name in ("Honeycutt (1992)", "Young (1994)", "Osborn et al. (2015)", "multiplied by β"):
        assert name in text, name
    for key in ("honeycutt1992", "young1994", "osborn2015"):
        assert "{" + key + "," in bib
