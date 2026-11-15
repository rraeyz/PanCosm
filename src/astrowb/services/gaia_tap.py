"""ADQL queries on the ESA Gaia archive (plans/architecture.md ARC-14)."""


def run(query):
    """The query now: synchronous, or through the archive's asynchronous queue when the synchronous queue is full
    (HTTP 503 "server overloaded", seen from the agent's network on 2026-11-06)."""
    from astroquery.gaia import Gaia

    try:
        return Gaia.launch_job(query).get_results()
    except Exception as e:  # noqa: BLE001 - the queue is full or the answer timed out: the asynchronous queue
        if "503" not in str(e) and "overloaded" not in str(e).lower() and "timed out" not in str(e).lower():
            raise
        return Gaia.launch_job_async(query).get_results()
