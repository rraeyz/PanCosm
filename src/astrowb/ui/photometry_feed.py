"""Frames handed to the Photometry window's live mode from outside (CAL-22 / PHO-19): the Calibrate stage's
calibrated files. They join the next poll of live mode, ahead of what its own folder shows."""


def measuring(page):
    return page.live is not None and getattr(page, "_live_timer", None) is not None


def feed(page, paths):
    """Queue paths for live mode and measure them now when it runs; True when it is measuring."""
    page.live_fed = [*getattr(page, "live_fed", []), *map(str, paths)]
    if measuring(page):
        page.poll_live()
        return True
    return False


def take_fed(page, new):
    """The fed frames not yet measured, then the folder's new files that are not among them; marks them seen."""
    fed, page.live_fed = getattr(page, "live_fed", []), []
    page.live_seen.update(fed)
    return [*fed, *(p for p in new if p not in fed)]
