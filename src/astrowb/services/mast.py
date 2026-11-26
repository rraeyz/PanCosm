"""MAST time-series products (TESS, Kepler, K2; plans/architecture.md ARC-14): list, then download."""


def products(target, mission, observations=None):
    """The product list of target's light curves. LookupError-free: ValueError when the archive has none."""
    from astroquery.mast import Observations, conf

    observations = observations or Observations
    with conf.set_temp("timeout", 120):  # an archive that stops answering must not hold the task forever
        obs = observations.query_criteria(
            objectname=target, radius="0.001 deg", obs_collection=mission, dataproduct_type="timeseries"
        )
    if len(obs) == 0:
        raise ValueError(f"no {mission} light curves for {target}")
    return observations.get_product_list(obs)


def download(table, folder, observations=None):
    from astroquery.mast import Observations

    return (observations or Observations).download_products(table, download_dir=str(folder), cache=True)


def count(target, collection):
    """How many time-series observations of target the archive lists for collection (the installation check)."""
    from astroquery.mast import Observations

    return len(Observations.query_criteria(objectname=target, obs_collection=collection, dataproduct_type="timeseries"))


def tess_sectors(target, tesscut=None):
    """[{sector, camera, ccd}] of the TESS full-frame images that cover target (TESScut's sector list, kept a day)."""
    from .cache import cached

    def lookup():
        from astroquery.mast import Tesscut, conf

        with conf.set_temp("timeout", 120):
            rows = (tesscut or Tesscut).get_sectors(objectname=target)
        if len(rows) == 0:  # an error, not an answer: not kept, so a later look-up asks again
            raise ValueError(f"no TESS full-frame images of {target}")
        return [{"sector": int(r["sector"]), "camera": int(r["camera"]), "ccd": int(r["ccd"])} for r in rows]

    return cached("lightcurves", ("tesscut", str(target).strip()), lookup)


def tess_cutout(target, folder, size=15, sector=None, tesscut=None):
    """TESScut cut-outs (size × size pixels of the full-frame images, one pixel file per sector, or only the given
    sector) into folder; their paths. The same request again gives the files already there."""
    from pathlib import Path

    from .cache import cached, fresh

    folder = Path(folder)

    def fetch():
        from astroquery.mast import Tesscut, conf

        folder.mkdir(parents=True, exist_ok=True)
        with conf.set_temp("timeout", 600):  # a year of FFI cut-outs is tens of MB
            table = (tesscut or Tesscut).download_cutouts(
                objectname=target, size=int(size), sector=sector or None, path=str(folder)
            )
        if len(table) == 0:
            raise ValueError(f"no TESS full-frame images of {target}")
        return [str(p) for p in table["Local Path"]]

    request = ("tesscut", str(target).strip(), int(size), int(sector or 0), str(folder.resolve()))
    paths = cached("cutouts", request, fetch)
    if not all(Path(p).exists() for p in paths):  # moved or deleted since: download them again
        with fresh():
            paths = cached("cutouts", request, fetch)
    return paths
