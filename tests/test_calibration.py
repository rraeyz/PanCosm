"""Calibration on a synthetic night whose true sky signal is known, and cross-checks against ccdproc."""

import time
from pathlib import Path

import numpy as np
import pytest
from astropy.io import fits

from astrowb.calibration import masters
from astrowb.calibration.frames import classify, scan
from astrowb.calibration.matching import make_plan

NY, NX = 60, 80
BIAS_LEVEL, READ_NOISE = 500.0, 5.0
DARK_RATE, HOT_RATE = 0.05, 40.0  # ADU/s
SKY = 300.0
LIGHT_T, FLAT_T = 60.0, 2.0


def _truth():
    rng = np.random.default_rng(7)
    y, x = np.mgrid[:NY, :NX]
    bias_pattern = BIAS_LEVEL + 3.0 * np.sin(x / 7.0)
    dark_rate = np.full((NY, NX), DARK_RATE)
    hot = rng.integers(0, NY * NX, 25)
    dark_rate.flat[hot] = HOT_RATE
    r2 = ((x - NX / 2) ** 2 + (y - NY / 2) ** 2) / (NX / 2) ** 2
    flat = (1.0 - 0.25 * r2) * (1 + 0.02 * rng.standard_normal((NY, NX)))  # vignetting + pixel response
    stars = np.zeros((NY, NX))
    for cy, cx, a in [(20, 30, 5000), (40, 60, 2000), (15, 70, 800)]:
        stars += a * np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * 1.5**2))
    return bias_pattern, dark_rate, flat, stars


def _write(path, data, **hdr):
    h = fits.Header({"XBINNING": 1, "YBINNING": 1, "CCD-TEMP": -10.0, "GAIN": 100, **hdr})
    fits.PrimaryHDU(data.astype(np.float32), h).writeto(path)


@pytest.fixture(scope="module")
def night(tmp_path_factory):
    d = tmp_path_factory.mktemp("night")
    rng = np.random.default_rng(1)
    bias_pattern, dark_rate, flat, stars = _truth()

    def noise():
        return rng.normal(0, READ_NOISE, (NY, NX))

    for i in range(9):
        _write(d / f"bias_{i}.fits", bias_pattern + noise(), IMAGETYP="Bias Frame", EXPTIME=0.0)
    for i in range(7):
        frame = bias_pattern + dark_rate * LIGHT_T + noise()
        if i == 3:
            frame[5, 5] += 3000  # cosmic ray in one dark
        _write(d / f"dark_{i}.fits", frame, IMAGETYP="Dark Frame", EXPTIME=LIGHT_T)
    for i in range(7):
        level = 20000 + 500 * i
        _write(
            d / f"flat_V_{i}.fits",
            bias_pattern + dark_rate * FLAT_T + level * flat + noise() * 3,
            IMAGETYP="Flat Field",
            EXPTIME=FLAT_T,
            FILTER="V",
        )
    for i in range(3):
        _write(
            d / f"light_{i}.fits",
            bias_pattern + dark_rate * LIGHT_T + (SKY + stars) * flat + noise(),
            IMAGETYP="Light Frame",
            EXPTIME=LIGHT_T,
            FILTER="V",
            OBJECT="TEST",
            **{"DATE-OBS": f"2026-10-01T20:0{i}:00"},
        )
    _write(d / "light_R.fits", bias_pattern + SKY * flat, IMAGETYP="LIGHT", EXPTIME=LIGHT_T, FILTER="R")
    (d / "broken.fits").write_text("not a fits file")
    return d


@pytest.fixture(scope="module")
def built(night):
    frames, _ = scan(night)
    paths = {k: sorted(f.path for f in frames if f.kind == k) for k in ("bias", "dark", "flat")}
    bias, bh = masters.master_bias(paths["bias"])
    dark, dh = masters.master_dark(paths["dark"], bias)
    flat, fh = masters.master_flat(paths["flat"], bias, dark, dh)
    return bias, dark, dh, flat


@pytest.mark.parametrize(
    "value,kind",
    [
        ("Bias Frame", "bias"),
        ("ZERO", "bias"),
        ("Dark Frame", "dark"),
        ("Flat Field", "flat"),
        ("SKYFLAT", "flat"),
        ("Light Frame", "light"),
        ("object", "light"),
        ("Dark Flat", "dark"),
        ("comp", "arc"),  # IRAF and the TOFES echelle: a ThAr exposure
        ("ThAr", "arc"),
        ("Arc Lamp", "arc"),
    ],
)
def test_classify_header_conventions(value, kind):
    assert classify(fits.Header({"IMAGETYP": value})) == kind


def test_classify_fallbacks():
    assert classify(fits.Header(), "/data/M31_flat_003.fits") == "flat"
    assert classify(fits.Header({"EXPTIME": 0.0}), "x.fits") == "bias"
    assert classify(fits.Header({"EXPTIME": 10.0}), "x.fits") == "unknown"
    assert classify(fits.Header({"EXPTIME": 5.0}), "Arcturus_Object_5s-1.fit") == "light"  # not an 'arc'


def test_scan_and_plan(night):
    frames, problems = scan(night)
    assert [p for p, _ in problems] == [str(night / "broken.fits")]
    kinds = sorted(f.kind for f in frames)
    assert kinds.count("bias") == 9 and kinds.count("dark") == 7 and kinds.count("flat") == 7
    plan = make_plan(frames)
    assert len(plan.groups) == 3  # one bias, one dark, one flat (V) group
    v_lights = [e for e in plan.lights if "light_R" not in e["light"]]
    assert all(e["bias"] and e["dark"] and e["flat"] for e in v_lights)
    assert [(m[1]) for m in plan.missing] == ["flat"] and plan.missing[0][2]["filter"] == "R"


def test_masters_recover_truth(built):
    bias, dark, dh, flat = built
    bias_pattern, dark_rate, true_flat, _ = _truth()
    resid = bias - bias_pattern
    ideal = READ_NOISE / np.sqrt(9)
    # robust clipping of 9 frames also drops ~5 % of good values: noise ~11 % above the ideal
    assert abs(resid.mean()) < 0.1 and resid.std() < 1.2 * ideal and np.abs(resid).max() < 7 * ideal
    assert dh["BIASSUB"] and dh["EXPTIME"] == LIGHT_T
    np.testing.assert_allclose(dark / LIGHT_T, dark_rate, atol=6 * READ_NOISE / LIGHT_T)
    assert abs(dark[5, 5] - dark_rate[5, 5] * LIGHT_T) < 15  # cosmic ray rejected by clipping
    assert abs(np.median(flat) - 1) < 1e-6
    np.testing.assert_allclose(flat, true_flat / np.median(true_flat), rtol=0.01)


def test_calibrated_light_recovers_sky(built, night):
    bias, dark, dh, flat = built
    _, _, _, stars = _truth()
    light, h = masters.load(night / "light_0.fits")
    cal = masters.calibrate(light, h["EXPTIME"], bias, dark, dh, flat)
    sky = cal[stars < 1]
    assert abs(np.median(sky) - SKY * np.median(_truth()[2])) / SKY < 0.02  # vignetting removed up to the flat norm
    corner, centre = np.median(cal[:10, :10]), np.median(cal[25:35, 35:45])
    assert abs(corner / centre - 1) < 0.03  # flat field removed the 25 % vignetting


def test_matches_ccdproc_with_same_masters(built, night):
    ccdproc = pytest.importorskip("ccdproc")
    import astropy.units as u

    bias, dark, dh, flat = built
    light, h = masters.load(night / "light_1.fits")
    ours = masters.calibrate(light, h["EXPTIME"], bias, dark, dh, flat)
    ccd = ccdproc.CCDData(light, unit="adu", meta=h)
    ccd = ccdproc.subtract_bias(ccd, ccdproc.CCDData(bias, unit="adu"))
    ccd = ccdproc.subtract_dark(
        ccd, ccdproc.CCDData(dark, unit="adu", meta=dh), exposure_time="EXPTIME", exposure_unit=u.s, scale=True
    )
    ccd = ccdproc.flat_correct(ccd, ccdproc.CCDData(flat, unit="adu"), norm_value=1)
    np.testing.assert_allclose(ours, ccd.data, rtol=1e-5, atol=1e-3)


def test_dark_scaling_rules(built):
    bias, dark, dh, _ = built
    scaled = masters.dark_for(30.0, bias, dark, dh)
    np.testing.assert_allclose(scaled, dark / 2, rtol=1e-6)
    raw_header = fits.Header({"EXPTIME": 60.0, "BIASSUB": False})
    raw = dark + bias
    np.testing.assert_allclose(masters.dark_for(60.0, None, raw, raw_header), raw)  # light - raw dark
    np.testing.assert_allclose(masters.dark_for(60.0, bias, raw, raw_header), dark, atol=1e-3)
    with pytest.raises(masters.CalibrationError, match="cannot be scaled"):
        masters.dark_for(30.0, None, raw, raw_header)


def test_block_reading_gives_same_result(night, monkeypatch):
    paths = sorted(str(p) for p in night.glob("bias_*.fits"))
    whole, _ = masters.master_bias(paths)
    monkeypatch.setattr(masters, "MEMORY_BUDGET", 9 * NX * 4 * 7)  # 7 rows per block
    blocks, _ = masters.master_bias(paths)
    np.testing.assert_array_equal(whole, blocks)


def test_unsigned_16bit_frames(tmp_path):
    data = np.array([[0, 1000], [40000, 65535]], dtype=np.uint16)
    hdu = fits.PrimaryHDU(data)  # astropy stores uint16 as int16 + BZERO 32768
    for i in range(3):
        hdu.writeto(tmp_path / f"b{i}.fits")
    img, _ = masters.master_bias(sorted(tmp_path.glob("b*.fits")))
    np.testing.assert_array_equal(img, data.astype(np.float32))


def test_mixed_sizes_and_exposures_rejected(tmp_path):
    _write(tmp_path / "a.fits", np.zeros((4, 4)), EXPTIME=10.0)
    _write(tmp_path / "b.fits", np.zeros((5, 4)), EXPTIME=10.0)
    _write(tmp_path / "c.fits", np.zeros((4, 4)), EXPTIME=20.0)
    with pytest.raises(masters.CalibrationError, match="different sizes"):
        masters.master_bias([tmp_path / "a.fits", tmp_path / "b.fits"])
    with pytest.raises(masters.CalibrationError, match="different exposure"):
        masters.master_dark([tmp_path / "a.fits", tmp_path / "c.fits"])


def test_calibration_steps_end_to_end(night, tmp_path):
    from astrowb.engine.core import Engine
    from astrowb.engine.project import Project
    from astrowb.engine.tasks import TaskQueue

    q = TaskQueue(max_workers=1)
    try:
        with Project(tmp_path / "p.astroproj") as project:
            eng = Engine(project, q)
            out = eng.run_chain(
                ["calibration.scan", "calibration.run"],
                {"folder": str(night), "output_dir": str(tmp_path / "cal")},
                {"calibration.run": {"cosmic_rays": True}},
            )
            assert len(out["masters"]) == 3 and len(out["calibrated"]) == 4
            assert [m[1] for m in out["missing"]] == ["flat"]  # R light: calibrated without flat, and reported
            h = fits.getheader(tmp_path / "cal" / "light_0.fits")
            assert h["CALF"].startswith("master_flat") and "CRCLEAN" in h
            r = fits.getheader(tmp_path / "cal" / "light_R.fits")
            assert r["CALF"] == "none" and r["CALB"].startswith("master_bias")
            time.sleep(0.3)  # runs are recorded on the task monitor thread
            assert [run["step"] for run in project.runs()] == ["calibration.scan", "calibration.run"]
    finally:
        q.shutdown()


def test_section_overscan_and_trim(tmp_path):
    assert masters.section("[1:70, 1:60]") == (slice(0, 60), slice(0, 70))
    assert masters.section("[80:72,1:60]") == (slice(0, 60), slice(71, 80)) and masters.section("bad") is None
    assert masters.section("[1:4096, :]") == (slice(None), slice(0, 4096))  # MaxIm DL on a real camera
    assert masters.section("[*,2:5]") == (slice(1, 5), slice(None)) and masters.section("[4096:4109]") is None
    rng = np.random.default_rng(3)
    paths = []
    for i, level in enumerate((480.0, 520.0)):  # the bias level drifts between frames
        img = np.full((NY, NX), level) + rng.normal(0, 2, (NY, NX))
        img[:, :70] += 100.0 * (i + 1)  # the exposed part; columns 72-80 are the overscan
        h = {"BIASSEC": "[72:80,1:60]", "TRIMSEC": "[1:70,1:60]"}
        _write(tmp_path / f"o{i}.fits", img, IMAGETYP="Bias Frame", EXPTIME=0.0, **h)
        paths.append(tmp_path / f"o{i}.fits")
    data, h = masters.load(paths[1])
    assert data.shape == (NY, 70) and np.median(data) == pytest.approx(200, abs=1)
    assert h["OVERSCAN"] == pytest.approx(520, abs=1) and "TRIMSEC" not in h and "BIASSEC" not in h
    combined, _, _ = masters.combine_files(paths)  # read in row blocks with the same correction
    assert combined.shape == (NY, 70) and np.median(combined) == pytest.approx(150, abs=1)
    _write(tmp_path / "m.fits", np.ones((NY, NX)), IMAGETYP="Bias Frame", EXPTIME=0.0, TRIMSEC="[1:70, :]")
    assert masters.load(tmp_path / "m.fits")[0].shape == (NY, 70)  # the whole y axis written as ':'
    # LCO FLOYDS: TRIMSEC 'UNKNOWN' and a DATASEC over the whole width, the overscan included
    img = np.full((NY, NX), 500.0)
    img[:, :70] += 100.0
    floyds = {"TRIMSEC": "UNKNOWN", "DATASEC": f"[1:{NX},1:{NY}]", "BIASSEC": f"[72:{NX},1:{NY}]"}
    _write(tmp_path / "f.fits", img, IMAGETYP="Bias Frame", EXPTIME=0.0, **floyds)
    data, _ = masters.load(tmp_path / "f.fits")
    assert data.shape == (NY, 71) and np.median(data) == pytest.approx(100, abs=1)
    rows, cols = masters._without_overscan((slice(0, 60), slice(0, 80)), (slice(0, 60), slice(0, 8)))
    assert cols == slice(8, 80) and rows == slice(0, 60)  # an overscan strip on the left


def test_dark_scale_and_defects(built, night):
    bias, dark, dh, flat = built
    _, dark_rate, _, _ = _truth()
    rng = np.random.default_rng(5)
    signal = masters.dark_for(LIGHT_T, bias, dark, dh)
    light_minus_bias = 0.7 * signal + SKY + rng.normal(0, READ_NOISE, (NY, NX))  # warmer camera: 70 % dark
    assert masters.dark_scale(light_minus_bias, signal) == pytest.approx(0.7, abs=0.03)
    dead = flat.copy()
    dead[10, 10] = 0.05
    bad = masters.defect_map(signal, dead)
    assert bad[10, 10] and set(np.flatnonzero(dark_rate == HOT_RATE)) <= set(np.flatnonzero(bad))
    img = np.full((NY, NX), 100.0, np.float32)
    img[bad] = 9999.0
    assert np.allclose(masters.repair(img, bad), 100.0)


def test_calibration_with_dark_optimisation_and_defect_repair(night, tmp_path):
    from astrowb.engine.steps import execute

    class Ctx:
        def progress(self, *a):
            pass

        def check(self):
            pass

    frames = execute("calibration.scan", {"folder": str(night)}, {}, Ctx())["frames"]
    out = execute(
        "calibration.run",
        {"frames": frames, "output_dir": str(tmp_path / "cal")},
        {"optimize_dark": True, "fix_defects": True},
        Ctx(),
    )
    assert any(Path(m).name.startswith("defects_") for m in out["masters"])
    h = fits.getheader(tmp_path / "cal" / "light_0.fits")
    assert h["DARKSCAL"] == pytest.approx(1.0, abs=0.05) and "repaired" in h.comments["CALDEF"]
    assert len(out["dark_scales"]) == len(out["calibrated"]) and h["DARKSCAL"] in [
        round(k, 4) for k in out["dark_scales"]
    ]
    sky = fits.getdata(tmp_path / "cal" / "light_0.fits")
    _, dark_rate, _, _ = _truth()
    hot = dark_rate == HOT_RATE
    assert np.abs(sky[hot] - SKY).max() < 60  # hot pixels repaired to the sky level


def test_spectra_are_not_divided_by_the_flat(night, tmp_path):
    from astrowb.engine.steps import execute

    class Ctx:
        def progress(self, *a):
            pass

        def check(self):
            pass

    frames = execute("calibration.scan", {"folder": str(night)}, {}, Ctx())["frames"]
    out = execute(
        "calibration.run",
        {"frames": frames, "output_dir": str(tmp_path / "cal")},
        {"divide_flat": False, "fix_defects": True},
        Ctx(),
    )
    assert any(Path(m).name.startswith("master_flat") for m in out["masters"])  # still made for the spectra
    h = fits.getheader(tmp_path / "cal" / "light_0.fits")
    assert h["CALF"] == "none" and h["CALB"].startswith("master_bias")
    _, _, flat, stars = _truth()
    sky = fits.getdata(tmp_path / "cal" / "light_0.fits")
    quiet = stars < 1
    assert np.median(sky[quiet] / (SKY * flat[quiet])) == pytest.approx(1.0, abs=0.02)  # bias and dark only


def test_dead_flat_pixels_become_nan_not_huge():
    """A real master flat (Palomar LFC) has dead columns at 1e-5 of the median: dividing gave values of 1e8."""
    light = np.full((20, 30), 1000.0, np.float32)
    flat = np.ones((20, 30), np.float32)
    flat[:, 5] = 2e-5  # dead column
    flat[3, 7] = 0.3  # deep vignetting is still light
    out = masters.calibrate(light, 10.0, flat=flat)
    assert np.isnan(out[:, 5]).all() and np.nanmax(out) == pytest.approx(1000 / 0.3, rel=1e-5)


def test_readout_settings_match_where_both_headers_state_them(tmp_path):
    """A real MaxIm DL night: the lights have READOUTM and READMODE, the bias, darks and flats only READOUTM.
    Nothing was matched and the lights were left uncalibrated; a real difference (another gain) still counts."""

    def write(name, kind, **keys):
        h = fits.Header({"IMAGETYP": kind, "EXPTIME": 0.0 if kind == "Bias Frame" else 90.0, "FILTER": "r"} | keys)
        fits.PrimaryHDU(np.zeros((NY, NX), np.float32), h).writeto(tmp_path / name)

    write("b.fit", "Bias Frame", READOUTM="Monochrome")
    write("d.fit", "Dark Frame", READOUTM="Monochrome")
    write("f.fit", "Flat Field", READOUTM="Monochrome")
    write("l.fit", "Light Frame", READOUTM="Monochrome", READMODE="Monochrome")
    write("g.fit", "Light Frame", READOUTM="Fast")
    frames, _ = scan(tmp_path)
    plan = make_plan(frames)
    entries = {Path(e["light"]).name: e for e in plan.lights}
    assert all(entries["l.fit"][k] for k in ("bias", "dark", "flat"))
    assert not any(entries["g.fit"][k] for k in ("bias", "dark", "flat"))


def test_arc_lamps_are_calibrated_without_flat_and_kept_apart(tmp_path):
    """The TOFES echelle night: ThAr frames (IMAGETYP 'comp') were 'unknown, ignored'."""
    from astrowb.calibration.steps import _run

    rng = np.random.default_rng(5)
    for i in range(3):
        _write(tmp_path / f"b{i}.fits", rng.normal(500, 3, (NY, NX)), IMAGETYP="bias", EXPTIME=0.0)
        _write(tmp_path / f"f{i}.fits", rng.normal(20500, 30, (NY, NX)), IMAGETYP="flat", EXPTIME=5.0)
    _write(tmp_path / "sci.fits", rng.normal(1500, 10, (NY, NX)), IMAGETYP="object", EXPTIME=30.0)
    _write(tmp_path / "thar.fits", rng.normal(900, 10, (NY, NX)), IMAGETYP="comp", EXPTIME=30.0)
    frames, _ = scan(tmp_path)

    class Ctx:
        def progress(self, *a):
            pass

        def check(self):
            pass

    out = _run(
        {"frames": [vars(f) for f in frames], "output_dir": str(tmp_path / "cal")},
        {
            "sigma": 3.0,
            "temp_tol": 2.0,
            "cosmic_rays": False,
            "read_noise": 10.0,
            "optimize_dark": False,
            "fix_defects": False,
            "divide_flat": True,
            "split_colour": False,
        },
        Ctx(),
    )
    assert [Path(p).name for p in out["arcs"]] == ["thar.fits"] and len(out["calibrated"]) == 1
    h = fits.getheader(out["arcs"][0])
    assert h["CALF"] == "none" and h["CALB"].startswith("master_bias")  # bias taken off, never flat-fielded
    assert not [m for m in out["missing"] if "thar" in m[0]]  # no "no flat" warning for a lamp


def test_eso_raw_frames_are_classified_with_their_grism():
    # ESO writes no IMAGETYP: DPR TYPE says BIAS, FLAT, STD, WAVE, OBJECT; a flat of grism 16 must not be used for a
    # spectrum of grism 11; binning in DET WIN1 BINX (a real EFOSC2 night, PESSTO, 2019-01-01)
    from astropy.io import fits as _fits

    from astrowb.calibration.frames import classify, read_frame

    def header(kind, grism, filt="Free"):
        h = _fits.Header()
        h["HIERARCH ESO DPR TYPE"] = kind
        h["HIERARCH ESO INS GRIS1 NAME"] = grism
        h["HIERARCH ESO INS FILT1 NAME"] = filt
        h["HIERARCH ESO DET WIN1 BINX"], h["HIERARCH ESO DET WIN1 BINY"] = 2, 2
        h["EXPTIME"] = 80.0
        return h

    assert [classify(header(k, "Gr#11")) for k in ("BIAS", "FLAT", "STD", "WAVE", "OBJECT")] == [
        "bias", "flat", "light", "arc", "light"
    ]  # fmt: skip
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "f.fits"
        _fits.PrimaryHDU(np.zeros((10, 10), np.float32), header("FLAT", "Gr#16", "OG530")).writeto(p)
        f = read_frame(p)
        assert f.filter == "OG530 / Gr#16" and f.binning == (2, 2) and f.kind == "flat"
