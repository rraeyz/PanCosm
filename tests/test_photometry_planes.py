"""PHO-36 with the mask and variance planes (CAL-13): DQ bits inside an aperture give B, S, C, T on exactly their
frames and stars; a flagged sky pixel is not used; the VAR plane's error equals the CCD-equation error."""

import numpy as np
from test_apertures import STARS, field

from astrowb.core import planes
from astrowb.photometry.aperture import measure
from astrowb.photometry.lightcurve import light_curve
from astrowb.photometry.planes_use import letters, merge, sky_mask

N, TX, TY = 25, int(STARS[0][0]), int(STARS[0][1])


def _night(folder, with_planes):
    paths = []
    for i in range(N):
        raw = field(4.0, seed=100 + i)
        f = planes.Frame.from_raw(raw, 1.0, 8.0, saturation=65000)  # the gain and read noise `field` is made with
        if i in range(10, 15):
            f.dq[TY + 1, TX] |= planes.BAD
        if i == 20:
            f.dq[:, TX - 1 : TX + 2] |= planes.TRAIL
        f.header = {"DATE-OBS": f"2026-11-15T20:{i:02d}:00", "EXPTIME": 30.0}
        p = folder / f"n{i}.fits"
        planes.write(p, f) if with_planes else planes.write(p, planes.Frame(f.sci, None, None, f.header))
        paths.append(p)
    return paths


def _run(paths):
    xy = [s[:2] for s in STARS]
    return light_curve(paths, xy[0], xy[1:3], 6, 15, 20, gain=1.0)


def test_dq_letters_on_their_frames_and_var_error_equals_the_formula(tmp_path):
    (a, b) = (tmp_path / "a", tmp_path / "b")
    a.mkdir(), b.mkdir()
    lc, plain = _run(_night(a, True)), _run(_night(b, False))
    got = [row[0] for row in lc["flags"]]
    assert got == ["B" if 10 <= i <= 14 else "T" if i == 20 else "" for i in range(N)]
    assert all(row[1] == "" and row[2] == "" for row in lc["flags"])  # the comparison stars are 40 px or more away
    assert all(row[0] == "" for row in plain["flags"])  # frames without planes behave as before
    from astrowb.photometry.measurements import measurements

    assert measurements(lc)[1][(10, "Flags_T1")] == "bad pixel or no data"
    clean = [i for i in range(N) if i not in (10, 11, 12, 13, 14, 20)]
    ratio = np.array(lc["target_flux_err"])[clean] / np.array(plain["target_flux_err"])[clean]
    assert abs(np.median(ratio) - 1) < 0.03, np.median(ratio)


def test_flagged_sky_pixel_is_not_used():
    img = field(4.0, seed=5)
    dq = np.zeros(img.shape, np.uint8)
    dq[TY + 17, TX] |= planes.BAD
    dq[TY, TX + 18] |= planes.NONLINEAR  # non-linear pixels still count for the sky
    assert sky_mask(dq).sum() == 1
    xy = [STARS[0][:2]]
    ref = measure(img, xy, 6, 15, 20, 1.0, sky_mask=sky_mask(dq))
    img[TY + 17, TX] = 1e9
    assert measure(img, xy, 6, 15, 20, 1.0, sky_mask=sky_mask(dq)) == ref


def test_letters_and_merge():
    dq = np.zeros((30, 30), np.uint8)
    dq[10, 10] = planes.SATURATED
    dq[10, 11] = planes.COSMIC | planes.REPAIRED
    dq[20, 20] = planes.NODATA
    assert letters(dq, [(10, 10), (20, 20), (np.nan, 1), (2, 2)], 2.0) == ["SC", "B", "", ""]
    assert merge(["C", "E"], ["SC", ""]) == ["CS", "E"]
