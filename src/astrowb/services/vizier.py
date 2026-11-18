"""VizieR cone and constraint queries (plans/architecture.md ARC-14) on the first CDS mirror that answers."""


def region(centre, radius, catalog, columns, row_limit, column_filters=None, first=False):
    """astroquery TableList of catalog around centre (SkyCoord) within radius (Quantity); first: only its first table
    ([] when none), so that a server with no rows for the region counts as empty and the next one is asked."""
    from astroquery.vizier import Vizier

    from .mirrors import cds

    def ask(server):
        v = Vizier(columns=columns, row_limit=row_limit, vizier_server=server)
        if column_filters:
            v.column_filters = column_filters
        tables = v.query_region(centre, radius=radius, catalog=catalog)
        return (tables[0] if len(tables) else []) if first else tables

    return cds("vizier", ask)


def constraints(catalog, columns, row_limit, **where):
    from astroquery.vizier import Vizier

    from .mirrors import cds

    return cds("vizier", lambda server: Vizier(columns=columns, row_limit=row_limit, vizier_server=server)
               .query_constraints(catalog=catalog, **where))  # fmt: skip
