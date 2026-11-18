"""SIMBAD object look-up (plans/architecture.md ARC-14): one name, cached, with the CDS mirror fall-back."""


def object_table(name, fetch=None):
    """SIMBAD's table for name (astropy Table with the V magnitude, or None when unknown). Offline: names looked up
    before still resolve. fetch(server) replaces the astroquery call (tests)."""
    from .cache import cached
    from .mirrors import cds

    def query(server):
        from astroquery.simbad import Simbad

        s = Simbad()
        s.server = server
        s.add_votable_fields("V")
        return s.query_object(name)

    return cached("simbad", name, lambda: cds("simbad", fetch or query))
