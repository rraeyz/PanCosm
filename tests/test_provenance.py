"""ARC-11: products carry how they were made, readable by people (HISTORY) and by the program (read)."""

import numpy as np
from astropy.io import fits
from astropy.table import Table

from astrowb.core import provenance


def test_record_round_trips_through_fits_and_ecsv(tmp_path):
    raw = tmp_path / "light 1.fits"  # a space in a name: FITS drops trailing spaces of cards
    fits.PrimaryHDU(np.zeros((8, 8), np.float32)).writeto(raw)
    rec = provenance.record("calibration.run", {"sigma": 3.0, "note": "a b  c ", "path": tmp_path}, {"light": raw})
    header = provenance.to_fits(fits.Header(), rec)
    out = tmp_path / "out.fits"
    fits.PrimaryHDU(np.zeros((8, 8), np.float32), header).writeto(out)
    assert provenance.read(out) == rec
    h = fits.getheader(out)
    assert h["PROCSTEP"] == "calibration.run" and h["PROCHASH"] == provenance.digest(rec) and h["SWVERS"]
    assert any("sigma = 3.0" in str(v) for v in h["HISTORY"])  # what a person reads in DS9
    t = Table({"x": [1, 2]})
    t.meta = provenance.to_ecsv(t.meta, rec)
    t.write(tmp_path / "t.ecsv")
    assert provenance.read(tmp_path / "t.ecsv") == rec


def test_checksum_sees_a_change_and_the_hash_ignores_the_time(tmp_path):
    f = tmp_path / "big.bin"
    data = bytearray(9 << 20)
    f.write_bytes(data)
    first = provenance.checksum(f)
    data[-10] = 1
    f.write_bytes(data)
    assert provenance.checksum(f) != first
    a = provenance.record("s", {"k": 1}, {"in": f})
    b = dict(a, made="2000-01-01T00:00:00+00:00")
    assert provenance.digest(a) == provenance.digest(b)
    assert provenance.digest(a) != provenance.digest(dict(a, params={"k": 2}))


def test_the_last_record_wins_when_a_file_went_through_two_steps():
    h = fits.Header()
    provenance.to_fits(h, {"step": "one", "params": {}, "inputs": {}, "versions": {"application": "1"}, "made": "t"})
    second = {"step": "two", "params": {"x": 1}, "inputs": {}, "versions": {"application": "1"}, "made": "t"}
    provenance.to_fits(h, second)
    assert provenance.from_header(h) == second and provenance.from_header(fits.Header()) is None


def test_every_fits_product_of_a_step_carries_its_record(tmp_path):
    from astrowb.engine.steps import execute

    class Ctx:
        def progress(self, *a):
            pass

        def check(self):
            pass

    src = tmp_path / "in.fits"
    fits.PrimaryHDU(np.ones((16, 16), np.float32)).writeto(src)
    out = tmp_path / "out.fits"
    execute("image.process", {"image": str(src), "operation": "median", "output": str(out)}, {}, Ctx())
    rec = provenance.read(out)
    assert rec["step"] == "image.process" and rec["inputs"]["image"][0]["name"] == "in.fits"
    assert "blake2" in rec["inputs"]["image"][0] and "output" not in rec["inputs"]  # the product is not its input
    assert provenance.read(src) is None  # the input is left as it was


def test_many_inputs_are_named_without_checksums(tmp_path):
    paths = []
    for i in range(provenance.MAX_CHECKSUMS + 1):
        paths.append(tmp_path / f"f{i}.fits")
        paths[-1].write_bytes(b"x")
    rec = provenance.record("s", {}, {"images": paths, "note": "text, not a file"})
    assert len(rec["inputs"]["images"]) == len(paths) and "blake2" not in rec["inputs"]["images"][0]


def test_input_frames_listed_in_the_outputs_are_left_alone(tmp_path):
    from astrowb.engine.steps import _mark_products

    frame = tmp_path / "light.fits"
    fits.PrimaryHDU(np.ones((4, 4), np.float32)).writeto(frame)
    _mark_products("photometry.quality", {"images": [str(frame)]}, {}, {"good": [str(frame)]}, 0.0)
    assert provenance.read(frame) is None


def test_ecsv_products_carry_the_record_too(tmp_path):
    """ARC-11: a table a step writes as ECSV carries how it was made, in its meta; CSV is left as it is."""
    import time

    from astropy.table import Table

    from astrowb.engine.steps import _mark_products

    src = tmp_path / "in.fits"
    fits.PrimaryHDU(np.ones((4, 4), np.float32)).writeto(src)
    table, plain = tmp_path / "lc.ecsv", tmp_path / "lc.csv"
    Table({"bjd": [2460512.123456789], "mag": [12.3]}).write(table, format="ascii.ecsv")
    plain.write_text("bjd,mag\n1,2\n")
    _mark_products("photometry.light_curve", {"images": [str(src)]}, {"r": 5}, {"table": str(table),
                   "csv": str(plain)}, time.time())  # fmt: skip
    rec = provenance.read(table)
    assert rec["step"] == "photometry.light_curve" and rec["params"] == {"r": 5}
    assert Table.read(table)["bjd"][0] == 2460512.123456789 and plain.read_text() == "bjd,mag\n1,2\n"


def test_a_product_names_the_online_answers_its_step_used(tmp_path, monkeypatch):
    """ARC-14 item 4: the record lists each catalogue asked and when its answer was fetched; the hash ignores it."""
    from types import SimpleNamespace

    from astrowb import settings
    from astrowb.engine import steps
    from astrowb.services import cache

    monkeypatch.setenv(settings.ENV_CONFIG_DIR, str(tmp_path))
    out = tmp_path / "out.fits"

    def func(inputs, params, ctx):
        cache.cached("vizier", "cone", lambda: 3)
        fits.PrimaryHDU(np.ones((4, 4), np.float32)).writeto(out)
        return {"image": str(out)}

    fake = SimpleNamespace(inputs=[], outputs=["image"], defaults={}, func=func)
    monkeypatch.setattr(steps, "get", lambda _id: fake)
    cache.last["simbad"] = (0.0, True)  # from before the step: not its own
    steps.execute("test.fetch", {}, {}, None)
    rec = provenance.read(out)
    assert list(rec["services"]) == ["vizier"] and rec["services"]["vizier"].startswith("20")
    assert "online: vizier" in str(fits.getheader(out)["HISTORY"])
    assert provenance.digest(rec) == provenance.digest({k: v for k, v in rec.items() if k != "services"})
