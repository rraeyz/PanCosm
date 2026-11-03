"""Remote-sensing formats besides GeoTIFF: HDF5 / NetCDF-4, NetCDF-3, JPEG2000."""

import numpy as np
import pytest

from astrowb.remotesensing import raster

LAT = np.linspace(36.0, 36.9, 10)  # cell centres, rows going north (CF habit)
LON = np.linspace(30.0, 31.1, 12)


def bands():
    yy, xx = np.mgrid[:10, :12]
    return (100 + xx + 10 * yy).astype(np.float32), (500 - xx).astype(np.float32)


def test_netcdf4_hdf5_with_cf_coordinates(tmp_path):
    import h5py

    red, nir = bands()
    with h5py.File(tmp_path / "s.nc", "w") as f:
        f["lat"], f["lon"] = LAT, LON
        f["red"] = red
        d = f.create_dataset("nir", data=nir)
        d.attrs["_FillValue"] = np.float32(500)
    r = raster.read(tmp_path / "s.nc")
    assert r.names == ["nir", "red"] or r.names == ["red", "nir"]
    i = r.names.index("red")
    assert np.array_equal(r.bands[i], red) and np.isnan(r.bands[r.names.index("nir")][0, 0])  # fill value
    assert r.epsg == 4326 and r.lonlat(0.5, 0.5) == pytest.approx((30.0, 36.0), abs=1e-6)  # centre of cell (0, 0)
    out = tmp_path / "ndvi.tif"
    raster.write(out, r, r.bands[i])
    back = raster.read(out)
    assert back.lonlat(0.5, 0.5) == pytest.approx((30.0, 36.9), abs=1e-5)  # written north-up: top row is north
    assert back.bands[0][0, 0] == red[-1, 0]


def test_netcdf3_classic(tmp_path):
    from scipy.io import netcdf_file

    red, _ = bands()
    with netcdf_file(tmp_path / "c.nc", "w") as f:
        f.createDimension("lat", 10)
        f.createDimension("lon", 12)
        f.createVariable("lat", "f8", ("lat",))[:] = LAT
        f.createVariable("lon", "f8", ("lon",))[:] = LON
        f.createVariable("temp", "f4", ("lat", "lon"))[:] = red
    r = raster.read(tmp_path / "c.nc")
    assert r.names == ["temp"] and np.array_equal(r.bands[0], red) and r.epsg == 4326


def test_jpeg2000(tmp_path):
    import imagecodecs

    red, _ = bands()
    (tmp_path / "b04.jp2").write_bytes(imagecodecs.jpeg2k_encode(red.astype(np.uint16), level=0))  # lossless
    r = raster.read(tmp_path / "b04.jp2")
    assert r.shape == (10, 12) and np.array_equal(r.bands[0], red)
