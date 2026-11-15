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
