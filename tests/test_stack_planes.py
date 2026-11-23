"""CAL-16: the stack carries VAR and DQ when its frames do (exact for a mean, NODATA where nothing was kept)."""

import numpy as np
from astropy.io import fits

from astrowb.calibration import masters, stacking
from astrowb.core import planes
from astrowb.photometry import planes_use

NY, NX, VAR = 20, 24, 4.0


def _frames(tmp_path, with_planes=True, n=5, cosmic=None):
    rng = np.random.default_rng(1)
    paths = []
    for i in range(n):
        img = 100 + rng.normal(0, 2, (NY, NX))
        dq = np.zeros((NY, NX), np.uint8)
        if cosmic and i == 0:
            img[cosmic] += 5000
            dq[cosmic] = planes.COSMIC
        f = planes.Frame(img, np.full((NY, NX), VAR), dq, {"FILTER": "V"})
        p = tmp_path / f"f{i}.fits"
        if with_planes:
            planes.write(p, f)
        else:
            fits.PrimaryHDU(img.astype(np.float32), fits.Header({"FILTER": "V"})).writeto(p)
        paths.append(p)
    return paths


def _stack(paths, **kw):
    kw = {"offsets": [(0.0, 0.0)] * len(paths), "rejection": "none"} | kw
    return stacking.stack(paths, with_planes=True, **kw)


def test_mean_without_rejection_divides_the_variance_by_n(tmp_path):
    img, cnt, header, (var, dq) = _stack(_frames(tmp_path))
    assert np.allclose(var, VAR / 5) and not dq.any()
    out = stacking.save_stack(tmp_path / "s.fits", img, cnt, header, (var, dq))
    with fits.open(out) as h:
        assert [x.name for x in h][1:] == ["SCI", "VAR", "DQ", "COVERAGE"]
    assert np.allclose(planes_use.read(out)[0], VAR / 5)
    assert np.allclose(masters.load(out)[0], img, atol=1e-3)  # the readers find SCI


def test_rejected_cosmic_pixel_has_variance_of_four_frames_and_no_flag(tmp_path):
    c = (7, 9)
    img, _, _, (var, dq) = _stack(_frames(tmp_path, cosmic=c), rejection="minmax", low=0, high=1)
    assert np.isclose(var[c], VAR / 4) and np.isclose(var[0, 0], VAR / 4)  # one highest value dropped everywhere
    img, _, _, (var, dq) = _stack(_frames(tmp_path, cosmic=c), rejection="sigma")
    assert np.isclose(var[c], VAR / 4) and dq[c] == 0  # the cosmic is not in the stack, so not in its DQ


def test_nodata_where_every_frame_is_rejected(tmp_path):
    paths = _frames(tmp_path)
    img, cnt, _, (var, dq) = _stack(paths[:1], offsets=[(2.0, 0.0)])  # shifted: the last two columns are empty
    assert (dq[:, -2:] == planes.NODATA).all() and (dq[:, :-2] == 0).all() and np.isnan(var[:, -2:]).all()


def test_common_dq_bits_only(tmp_path):
    paths = _frames(tmp_path)
    for k, p in enumerate(paths):
        with fits.open(p, mode="update") as h:
            h["DQ"].data[3, 3] = planes.SATURATED
            h["DQ"].data[4, 4] = planes.SATURATED if k else 0
    _, _, _, (_, dq) = _stack(paths)
    assert dq[3, 3] == planes.SATURATED and dq[4, 4] == 0


def test_integer_shift_variance_is_exact_and_fraction_uses_squared_weights(tmp_path):
    paths = _frames(tmp_path, n=2)
    _, _, _, (var, _) = _stack(paths, offsets=[(0.0, 0.0), (0.5, 0.0)])
    assert np.isclose(var[5, 5], (VAR + VAR * 0.5) / 4)  # frame 2: weights 0.5 / 0.5 -> 0.5 VAR


def test_plain_frames_give_todays_single_hdu(tmp_path):
    paths = _frames(tmp_path, with_planes=False)
    img, cnt, header, extra = _stack(paths)
    assert extra is None
    out = stacking.save_stack(tmp_path / "s.fits", img, cnt, header, extra)
    with fits.open(out) as h:
        assert [x.name for x in h] == ["PRIMARY", "COVERAGE"]
