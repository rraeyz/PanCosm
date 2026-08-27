"""One data model for images from the sky and from orbit: bands + coordinate system + metadata.

GeoTIFF / Cloud-Optimised GeoTIFF are read and written with tifffile; the GeoTIFF tags (pixel scale,
tie point or transformation matrix, GeoKey directory, nodata) are copied unchanged to every product,
so results stay georeferenced exactly like the input. FITS images and cubes read into the same model
(no map projection). Map coordinates follow the GeoTIFF affine model; latitude/longitude come from
pyproj when the EPSG code is known.
"""

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

GEO_TAGS = (33550, 33922, 34264, 34735, 34736, 34737)  # scale, tiepoint, transformation, GeoKeys, doubles, ascii
NODATA_TAG = 42113  # GDAL_NODATA (ASCII)


@dataclass
class Raster:
    bands: np.ndarray  # (n_bands, ny, nx) float32
    names: list = field(default_factory=list)
    transform: tuple | None = None  # (c, a, b, f, d, e): X = c + a*col + b*row, Y = f + d*col + e*row
    epsg: int | None = None
    nodata: float | None = None
    tags: dict = field(default_factory=dict)  # raw GeoTIFF tags {code: (dtype, count, value)}
    source: str = ""

    @property
    def shape(self):
        return self.bands.shape[1:]

    def band(self, i):
        b = self.bands[i]
        return np.where(b == self.nodata, np.nan, b) if self.nodata is not None else b

    def nan_bands(self):
        """All bands with the nodata value made NaN in place (no copy per band: a Sentinel-2 tile's bands are 1 GB),
        for a step's own raster that is not shown or written back."""
        if self.nodata is not None:
            self.bands[self.bands == self.nodata] = np.nan
            self.nodata = None
        return self.bands

    def map_xy(self, col, row):
        """Map coordinates of a pixel position (pixel centres at integer + 0.5 in the GeoTIFF area model)."""
        if self.transform is None:
            return None
        c, a, b, f, d, e = self.transform
        return c + a * col + b * row, f + d * col + e * row

    def lonlat(self, col, row):
        xy = self.map_xy(col, row)
        if xy is None or self.epsg is None:
            return None
        if self.epsg == 4326:
            return xy
        from pyproj import Transformer

        return Transformer.from_crs(self.epsg, 4326, always_xy=True).transform(*xy)


def _geokeys(directory):
    """{key id: value} from a GeoKeyDirectory (values stored inline only, which covers EPSG codes)."""
    keys = {}
    d = list(directory)
    for i in range(4, 4 + 4 * d[3], 4):
        key, location, _, value = d[i : i + 4]
        if location == 0:
            keys[key] = value
    return keys


HDF_SUFFIXES = (".h5", ".hdf5", ".he5", ".hdf", ".nc", ".nc4", ".cdf")
JP2_SUFFIXES = (".jp2", ".j2k", ".jpx")


def _regular(axis):
    """(start, step) of an evenly spaced coordinate axis, else None."""
    axis = np.asarray(axis, float).ravel()
    if len(axis) < 2:
        return None
    step = np.diff(axis)
    return (float(axis[0]), float(step.mean())) if np.allclose(step, step.mean(), rtol=1e-4) else None


def _cf_grid(lat, lon):
    """Raster transform (EPSG:4326) from 1-D CF latitude / longitude coordinate variables of cell centres."""
    la, lo = _regular(lat), _regular(lon)
    if la is None or lo is None:
        return None
    return (lo[0] - lo[1] / 2, lo[1], 0.0, la[0] - la[1] / 2, 0.0, la[1])


def _read_hdf(path):
    """HDF5 / NetCDF-4 (h5py), NetCDF-3 (scipy): every 2-D numeric variable of the largest common shape is a
    band (3-D variables: one band per plane); CF lat / lon coordinates give the map position."""
    arrays, coords = {}, {}
    try:
        import h5py

        with h5py.File(path, "r") as f:

            def visit(name, obj):
                if isinstance(obj, h5py.Dataset) and obj.dtype.kind in "fiu" and obj.ndim in (1, 2, 3):
                    key = name.split("/")[-1]
                    (coords if obj.ndim == 1 else arrays)[key] = np.asarray(obj[()], np.float32)
                    fill = obj.attrs.get("_FillValue")
                    if fill is not None and obj.ndim > 1:
                        arrays[key][arrays[key] == np.float32(np.ravel(fill)[0])] = np.nan

            f.visititems(visit)
    except OSError:  # not HDF5: a classic NetCDF-3 file
        from scipy.io import netcdf_file

        with netcdf_file(path, "r", mmap=False) as f:
            for key, var in f.variables.items():
                a = np.asarray(var.data, np.float32)
                fill = getattr(var, "_FillValue", None)
                if fill is not None:
                    a[a == np.float32(fill)] = np.nan
                (coords if a.ndim == 1 else arrays)[key] = a
    if not arrays:
        raise ValueError("no image (2-D variable) in this file")
    planes = {}
    for key, a in arrays.items():
        if a.ndim == 2:
            planes[key] = a
        else:
            planes.update({f"{key}[{i}]": a[i] for i in range(a.shape[0])})
    shape = max({p.shape for p in planes.values()}, key=lambda s: s[0] * s[1])
    names = [k for k, p in planes.items() if p.shape == shape]
    lat = next((coords[k] for k in ("lat", "latitude", "y") if k in coords and len(coords[k]) == shape[0]), None)
    lon = next((coords[k] for k in ("lon", "longitude", "x") if k in coords and len(coords[k]) == shape[1]), None)
    transform = _cf_grid(lat, lon) if lat is not None and lon is not None else None
    return Raster(np.stack([planes[k] for k in names]), names, transform, 4326 if transform else None, source=str(path))


def read(path) -> Raster:
    if ";" in str(path):  # several files of one scene (Sentinel-2, Landsat: one band per file)
        return read_bands(str(path).split(";"))
    path = Path(path)
    if path.suffix.lower() in HDF_SUFFIXES:
        return _read_hdf(path)
    if path.suffix.lower() in JP2_SUFFIXES:  # Sentinel-2 bands: one band per file
        import imagecodecs

        data = np.asarray(imagecodecs.imread(str(path)), np.float32)
        bands = data[None] if data.ndim == 2 else np.moveaxis(data, -1, 0)
        level = safe_reflectance(path)
        if level is not None:  # a band of an ESA Sentinel-2 product: numbers to reflectance, 0 = no data
            offset, quantification = level
            bands[bands == 0] = np.nan
            bands += np.float32(offset)
            bands /= np.float32(quantification)
        # shortcut: the GeoJP2 / GML map position is not read; convert with GDAL when map coordinates matter
        return Raster(bands, [f"B{i + 1}" for i in range(len(bands))], source=str(path))
    if path.suffix.lower() in (".fits", ".fit", ".fts"):
        from astropy.io import fits

        from ..io.fits import find_image_hdu

        with fits.open(path) as hdul:
            data = np.asarray(hdul[find_image_hdu(hdul)].data, np.float32)
        bands = data[None] if data.ndim == 2 else data.reshape(-1, *data.shape[-2:])
        return Raster(bands, [f"B{i + 1}" for i in range(len(bands))], source=str(path))
    import tifffile

    with tifffile.TiffFile(path) as tif:
        page = tif.pages[0]
        data = page.asarray()
        planar = _planar(page, data.shape)
        if data.ndim == 2:
            bands = data[None]
        elif planar:
            bands = data
        else:
            bands = np.moveaxis(data, -1, 0)
        meta = _tiff_meta(page)
    return Raster(bands.astype(np.float32), [f"B{i + 1}" for i in range(len(bands))], *meta, str(path))


def _tiff_meta(page):
    """(transform, epsg, nodata, tags) from a GeoTIFF page's tags."""
    tags = {}
    for code in (*GEO_TAGS, NODATA_TAG):
        if code in page.tags:
            t = page.tags[code]
            tags[code] = (t.dtype, t.count, t.value)
    transform = None
    if 34264 in tags:  # full transformation matrix (4x4, row-major)
        m = tags[34264][2]
        transform = (m[3], m[0], m[1], m[7], m[4], m[5])
    elif 33550 in tags and 33922 in tags:
        sx, sy = tags[33550][2][:2]
        i, j, _, x, y, _ = tags[33922][2][:6]
        transform = (x - i * sx, sx, 0.0, y + j * sy, 0.0, -sy)
    epsg = None
    if 34735 in tags:
        keys = _geokeys(tags[34735][2])
        code = keys.get(3072) or keys.get(2048)  # ProjectedCSType, else GeographicType
        epsg = int(code) if code and code != 32767 else None
    nodata = None
    if NODATA_TAG in tags:
        try:
            nodata = float(str(tags[NODATA_TAG][2]).strip("\x00 "))
        except ValueError:
            nodata = None
    return transform, epsg, nodata, tags


TIFF_SUFFIXES = (".tif", ".tiff")


@dataclass
class Scene:
    """A GeoTIFF scene (one file, or one band per file) read by rows when it is asked for: what Raster holds whole,
    for scenes that do not fit the computer's memory. Same attributes as Raster but no `bands`."""

    files: list  # [(path, number of bands)]
    names: list
    shape: tuple
    transform: tuple | None = None
    epsg: int | None = None
    nodata: float | None = None
    tags: dict = field(default_factory=dict)
    source: str = ""

    map_xy = Raster.map_xy
    lonlat = Raster.lonlat

    @property
    def n_bands(self):
        return sum(n for _, n in self.files)

    def band(self, i):
        """Band i whole (nodata as NaN), reading only its file."""
        import tifffile

        for path, n in self.files:
            if i < n:
                with tifffile.TiffFile(path) as tif:
                    b = _tiff_rows(tif, 0, self.shape[0])[i]
                if self.nodata is not None:
                    b[b == self.nodata] = np.nan
                return b
            i -= n
        raise IndexError(i)

    def pixel(self, col, row):
        """Every band's value at one pixel (only the tiles of that row are read)."""
        return self.rows(int(row), int(row) + 1)[:, 0, int(col)]

    def subset(self, use):
        """The same scene with only the bands `use` (indices), still read by rows."""
        whole = self

        class Subset:
            n_bands, shape = len(use), self.shape

            @staticmethod
            def rows(r0, r1):
                return whole.rows(r0, r1)[list(use)]

        return Subset()

    def rows(self, r0, r1):
        """Every band's rows r0..r1 (n_bands, rows, nx) as float32, nodata as NaN; only the tiles or strips these
        rows touch are read and decoded."""
        import tifffile

        out = []
        for path, _ in self.files:
            with tifffile.TiffFile(path) as tif:
                out.append(_tiff_rows(tif, r0, r1))
        block = np.concatenate(out) if len(out) > 1 else out[0]
        if self.nodata is not None:
            block[block == self.nodata] = np.nan
        return block


def _tiff_rows(tif, r0, r1):
    """Rows r0..r1 of a TIFF's first image as (samples, rows, nx) float32, decoding only the segments that hold
    them (tifffile's own decoder: compression, predictor, tiles or strips, planar or interleaved)."""
    page = tif.pages[0]
    ny, nx = page.imagelength, page.imagewidth
    spp = page.samplesperpixel
    planes = spp if page.planarconfig == 2 else 1
    if page.is_tiled:
        ch, across = page.tilelength, -(-nx // page.tilewidth)
    else:
        ch, across = min(page.rowsperstrip or ny, ny), 1
    down = -(-ny // ch)
    r0, r1 = min(r0, ny), min(r1, ny)
    out = np.zeros((spp, r1 - r0, nx), np.float32)
    if r1 <= r0:
        return out
    fh = tif.filehandle
    wanted = [
        (plane * down + tr) * across + tc
        for plane in range(planes)
        for tr in range(r0 // ch, (r1 - 1) // ch + 1)
        for tc in range(across)
    ]
    wanted = [i for i in wanted if page.databytecounts[i]]  # an empty count is a sparse (empty) tile
    raw = []
    for i in wanted:  # read in file order, decoded on every core (zlib / deflate release the interpreter lock):
        fh.seek(page.dataoffsets[i])  # one by one it was 55 % slower than tifffile's whole-image read
        raw.append(fh.read(page.databytecounts[i]))

    def place(job):
        i, data = job
        seg, (s, _, y, x, _), _ = page.decode(data, i)
        seg = seg[0]  # (h, w, samples)
        a, b = max(y, r0), min(y + seg.shape[0], r1)
        w = min(seg.shape[1], nx - x)
        if b > a and w > 0:
            out[s : s + seg.shape[-1], a - r0 : b - r0, x : x + w] = np.moveaxis(seg[a - y : b - y, :w], -1, 0)

    if len(wanted) > 1:
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor() as pool:
            list(pool.map(place, zip(wanted, raw, strict=True)))
    elif wanted:
        place((wanted[0], raw[0]))
    return out


def open_scene(source) -> Scene | None:
    """The scene as a Scene (headers only) when every file is a GeoTIFF of one grid, else None."""
    import tifffile

    paths = str(source).split(";")
    if not all(Path(p).suffix.lower() in TIFF_SUFFIXES for p in paths):
        return None
    files, names, meta, shape = [], [], None, None
    for p in paths:
        with tifffile.TiffFile(p) as tif:
            page = tif.pages[0]
            n = page.samplesperpixel
            if shape is None:
                shape, meta = (page.imagelength, page.imagewidth), _tiff_meta(page)
            elif (page.imagelength, page.imagewidth) != shape:
                raise ValueError("the files are not the same size: open bands of one scene at the same resolution")
        files.append((p, n))
        if len(paths) == 1:
            names += [f"B{i + 1}" for i in range(n)]
        else:
            names += [Path(p).stem + ("" if n == 1 else f"_B{i + 1}") for i in range(n)]
    return Scene(files, names, shape, *meta, str(source))


def load(source, factor=3.0):
    """The scene whole (Raster) when `factor` times its float32 size fits the computer's free memory, else read by
    rows (Scene, GeoTIFF only): a 13-band Sentinel-2 tile is 6 GB in float32."""
    from ..engine.parallel import available_memory

    scene = open_scene(source)
    if scene is not None:
        free = available_memory()
        if free is not None and factor * 4 * scene.n_bands * scene.shape[0] * scene.shape[1] > free:
            return scene
    return read(source)


S2_BANDS = ("B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B09", "B10", "B11", "B12")  # band_id order


def safe_reflectance(path):
    """(offset, quantification) of a band file inside an ESA Sentinel-2 SAFE product, from its MTD_MSIL2A.xml /
    MTD_MSIL1C.xml: reflectance = (number + offset) / quantification. Since processing baseline 04.00 (January
    2022) the numbers carry +1000 (offset -1000); band math on the raw numbers is then wrong (red 0.05 and NIR 0.30
    gave NDVI 0.455 instead of 0.714). None for any other file (class maps such as SCL, other sources; Element84's
    Sentinel-2 COGs have the offset taken out already: earthsearch:boa_offset_applied)."""
    import re
    import xml.etree.ElementTree as ET

    m = re.search(r"_(B\d\d|B8A)(_\d+m)?\.jp2$", Path(path).name, re.IGNORECASE)
    if not m:
        return None
    band = m.group(1).upper()
    for parent in list(Path(path).resolve().parents)[:6]:
        for name in ("MTD_MSIL2A.xml", "MTD_MSIL1C.xml"):
            meta = parent / name
            if meta.is_file():
                try:
                    root = ET.parse(meta).getroot()
                except ET.ParseError:
                    return None
                quant, offset = 10000.0, 0.0
                for el in root.iter():
                    tag = el.tag.rsplit("}", 1)[-1]
                    if tag in ("BOA_QUANTIFICATION_VALUE", "QUANTIFICATION_VALUE") and el.text:
                        quant = float(el.text)
                    elif tag in ("BOA_ADD_OFFSET", "RADIO_ADD_OFFSET") and el.get("band_id") is not None:
                        if int(el.get("band_id")) == S2_BANDS.index(band) and el.text:
                            offset = float(el.text)
                return offset, quant
    return None


def _planar(page, shape):
    """Bands first (planar) or last (pixel-interleaved) in a TIFF page of this shape."""
    return page.planarconfig == 2 or (len(shape) == 3 and shape[0] < shape[-1] and shape[0] <= 16)


def band_count(path) -> int:
    """Bands of a GeoTIFF from its first page's shape, without reading the pixels (a product of a 120 Mpx scene)."""
    import tifffile

    with tifffile.TiffFile(path) as tif:
        page = tif.pages[0]
        shape = page.shape
    return 1 if len(shape) == 2 else (shape[0] if _planar(page, shape) else shape[-1])


def read_bands(paths) -> Raster:
    """Files of one scene on the same grid as one image: their bands in file order, named after the files (B04,
    B08…; "name_B2" for a file with several bands), the map position of the first. The source is the paths joined
    with ';', which read() takes back."""
    first = read(paths[0])
    meta, shape = (first.transform, first.epsg, first.nodata, first.tags), first.shape
    # every file is read into one array allocated once (concatenating kept the scene twice in memory, 1 GB more for
    # a Sentinel-2 tile); a file with more bands than the first makes it grow
    bands = np.empty((len(first.names) * len(paths), *shape), np.float32)
    names, used = [], 0
    for k, p in enumerate(paths):
        r = first if k == 0 else read(p)
        if r.shape != shape:
            raise ValueError("the files are not the same size: open bands of one scene at the same resolution")
        names += [Path(r.source).stem + ("" if len(r.names) == 1 else f"_{n}") for n in r.names]
        if used + len(r.names) > len(bands):
            bands = np.concatenate([bands[:used], np.empty((len(r.names), *shape), np.float32)])
        bands[used : used + len(r.names)] = r.bands
        used += len(r.names)
        r.bands = first.bands = None  # freed as soon as copied
    bands = bands[:used]
    return Raster(bands, names, *meta, ";".join(map(str, paths)))


def write(path, like: Raster, data, nodata=None):
    """Write a band (2-D) or bands (3-D) as GeoTIFF with the georeferencing of `like`."""
    import tifffile

    data = np.asarray(data, np.float32)
    extratags = [(code, dt, cnt, val, True) for code, (dt, cnt, val) in like.tags.items() if code in GEO_TAGS]
    if not extratags and like.transform and like.epsg:  # e.g. from NetCDF: write GeoTIFF tags of our own
        c, a, _, f, _, e = like.transform
        geographic = like.epsg == 4326
        keys = [
            1,
            1,
            0,
            3,
            1024,
            0,
            1,
            2 if geographic else 1,
            1025,
            0,
            1,
            1,
            2048 if geographic else 3072,
            0,
            1,
            like.epsg,
        ]
        if e > 0:  # rows going north (CF grids): GeoTIFF wants the tie point at the top row
            data = data[..., ::-1, :]
            f, e = f + e * data.shape[-2], -e
        extratags = [
            (33550, "d", 3, (a, -e, 0.0), True),
            (33922, "d", 6, (0.0, 0.0, 0.0, c, f, 0.0), True),
            (34735, "H", len(keys), tuple(keys), True),
        ]
    nd = nodata if nodata is not None else (np.nan if np.isnan(data).any() else None)
    if nd is not None:
        extratags.append((NODATA_TAG, "s", 0, str(nd), True))
    tifffile.imwrite(
        path,
        data,
        photometric="minisblack",
        planarconfig="separate" if data.ndim == 3 else None,
        extratags=extratags,
        compression="zlib",
    )
    return str(path)
