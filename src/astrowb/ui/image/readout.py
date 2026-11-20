"""The cursor read-out (ARC-7 item 5): the sky position of a pixel in sexagesimal and in degrees."""


def sky_text(wcs, x, y):
    """RA / Dec of the 0-based pixel (x, y) as "hh:mm:ss.s +dd:mm:ss.s (ra° dec°)"."""
    sky = wcs.pixel_to_world(x, y)
    return f"{sky.to_string('hmsdms', precision=1)} ({sky.ra.deg:.5f}° {sky.dec.deg:+.5f}°)"
