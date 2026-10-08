"""Does the installed application have every part it needs, and can it reach the services it uses?

offline(): every module of the application and every library it uses (many are imported only when a feature is
used, so a missing one shows up only then), and the functions that read data files shipped with a library
(projections, Earth orientation, line lists, catalogues of plugins and automations, codecs). The installers'
smoke test runs it, so a file the packager left out fails the build instead of a user's evening.

online(): one small request to every web service the application talks to (``--check-online``). A failure there
can be the network; the report says which service and why.
"""

import importlib
import pkgutil
import traceback

# Third-party modules the application imports, also those imported inside functions
# (tests/test_selfcheck.py keeps this list complete).
LIBRARIES = (
    "PIL",
    "alpaca.telescope",
    "astropy.coordinates",
    "astropy_iers_data",
    "astropy.io.fits",
    "astropy.stats",
    "astropy.table",
    "astropy.time",
    "astropy.timeseries",
    "astropy.units",
    "astropy.visualization",
    "astropy.wcs.utils",
    "astroquery.mast",
    "astroquery.simbad",
    "astroquery.vizier",
    "astroscrappy",
    "certifi",
    "contourpy",
    "cryptography.hazmat.primitives.asymmetric",
    "cryptography.x509.oid",
    "emcee",
    "h5py",
    "imagecodecs",
    "matplotlib.backends.backend_qtagg",
    "matplotlib.figure",
    "matplotlib.image",
    "matplotlib.pyplot",
    "matplotlib.widgets",
    "numpy",
    "photutils.aperture",
    "photutils.background",
    "photutils.centroids",
    "photutils.detection",
    "photutils.psf",
    "platformdirs",
    "pyproj",
    "pyqtgraph",
    "rawpy",
    "scipy.cluster.vq",
    "scipy.interpolate",
    "scipy.io",
    "scipy.ndimage",
    "scipy.optimize",
    "scipy.signal",
    "scipy.sparse",
    "scipy.spatial",
    "scipy.special",
    "shiboken6",
    "tifffile",
    "wgpu",
)


def _run(checks):
    """[(name, ok, detail)] for {name: function}; a check passes when it returns without an exception."""
    out = []
    for name, fn in checks.items():
        try:
            detail = fn()
            out.append((name, True, "" if detail is None else str(detail)))
        except Exception as e:  # report every failure, keep checking the rest
            out.append((name, False, f"{type(e).__name__}: {e}"[:300] or traceback.format_exc(limit=1)))
    return out


def _modules():
    import astrowb

    names = [m.name for m in pkgutil.walk_packages(astrowb.__path__, "astrowb.") if not m.name.endswith("__main__")]
    for name in names:
        importlib.import_module(name)
    return f"{len(names)} modules"


def _libraries():
    failed = []
    for name in LIBRARIES:
        try:
            importlib.import_module(name)
        except Exception as e:  # name every library that is missing or broken, not only the first
            failed.append(f"{name} ({type(e).__name__}: {e})")
    assert not failed, "; ".join(failed)
    return f"{len(LIBRARIES)} libraries"


def _projections():
    from pyproj import Transformer

    x, y = Transformer.from_crs(4326, 32635, always_xy=True).transform(27.0, 39.0)  # needs proj.db
    assert abs(x - 500000) < 1 and 4.3e6 < y < 4.4e6, (x, y)


def _time_and_place():
    import astropy.units as u
    from astropy.coordinates import EarthLocation, SkyCoord
    from astropy.time import Time

    from .timing import airmass, bjd_tdb

    site = EarthLocation(lat=39.9 * u.deg, lon=32.8 * u.deg, height=900 * u.m)
    star = SkyCoord(31.04 * u.deg, 46.69 * u.deg)
    t = Time("2025-01-10T20:00:00", scale="utc")  # covered by the Earth-orientation tables shipped with astropy
    shift = (bjd_tdb(t, star, site).jd - t.jd) * 86400
    assert abs(shift) < 600, shift
    assert airmass(t, star, site) > 0.99


def _line_lists():
    from .spectroscopy.wavecal import line_lists, load_line_list

    names = line_lists()
    assert names and all(len(load_line_list(n)) > 10 for n in names), names
    return f"{len(names)} line lists"


def _resources():
    from importlib.resources import files

    from .engine import automation, plugins

    guide = files("astrowb") / "resources" / "guide"
    chapters = {lang: len(list((guide / lang).iterdir())) for lang in ("en", "tr", "de", "es")}
    assert all(n >= 12 for n in chapters.values()), chapters
    assert len(list(plugins.examples_dir().glob("*.py"))) >= 1
    assert len(automation.available()) >= 5
    for lang in ("tr", "de", "es"):
        assert (files("astrowb") / "resources" / "i18n" / f"app_{lang}.qm").is_file(), lang


def _codecs():
    import io

    import h5py
    import imagecodecs
    import numpy as np
    import tifffile

    a = (np.arange(64 * 64) % 251).astype(np.uint8).reshape(64, 64)
    assert np.array_equal(imagecodecs.jpeg2k_decode(imagecodecs.jpeg2k_encode(a, level=0)), a)
    buf = io.BytesIO()
    tifffile.imwrite(buf, a)
    buf.seek(0)
    assert np.array_equal(tifffile.imread(buf), a)
    with h5py.File(io.BytesIO(), "w") as f:
        f["x"] = a
        assert f["x"][3, 3] == a[3, 3]


def _plot():
    import io

    from matplotlib.figure import Figure

    fig = Figure()
    fig.add_subplot().plot([0, 1], [1, 0])
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    assert buf.tell() > 1000


def _certificates():
    import os

    import certifi

    assert os.path.getsize(certifi.where()) > 10000


def offline():
    """Everything that needs no network. [(name, ok, detail)]"""
    return _run(
        {
            "application modules": _modules,
            "libraries": _libraries,
            "map projections (pyproj)": _projections,
            "times and places (astropy)": _time_and_place,
            "arc line lists": _line_lists,
            "guide, plugins, automations, translations": _resources,
            "image and data codecs": _codecs,
            "plots (matplotlib)": _plot,
            "certificates for HTTPS": _certificates,
        }
    )


def _head(url):
    import urllib.request

    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "astronomy-workbench-selfcheck"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return f"HTTP {r.status}"


def online():
    """One small request to every web service the application uses. [(name, ok, detail)]"""
    import astropy.units as u
    from astropy.coordinates import SkyCoord

    from . import overlays, updates
    from .photometry import catalog
    from .planning import ephemerides, targets
    from .spectroscopy import atmosphere, templates
    from .timeseries import surveys

    vega = SkyCoord(279.2347 * u.deg, 38.7837 * u.deg)

    def mast():
        from astroquery.mast import Observations

        rows = Observations.query_criteria(objectname="HAT-P-32", obs_collection="TESS", dataproduct_type="timeseries")
        return f"{len(rows)} TESS observations"

    def iers():
        from ..core import earth_orientation

        return earth_orientation.describe(earth_orientation.status())

    return _run(
        {
            "GitHub releases (update check)": lambda: updates.latest_release()["version"],
            "SIMBAD (target names)": lambda: targets._simbad("Vega").name,
            "VizieR: Gaia DR3 (overlays)": lambda: (
                f"{len(overlays.query_catalogue(vega.ra.deg, vega.dec.deg, 0.05, 'gaia', 12))} stars"
            ),
            "VizieR: APASS / Gaia (standard magnitudes)": lambda: f"{len(catalog.vizier_fetch(vega, 30.0))} catalogues",
            "VSX (variable-star ephemerides)": lambda: ephemerides.vsx("Algol"),
            "NASA Exoplanet Archive": lambda: ephemerides.exoplanet("HAT-P-32 b"),
            "IMCCE SkyBoT (asteroids and comets)": lambda: (
                f"{len(overlays.minor_planets(83.8, 22.0, 0.5, 2461000.5))} objects"
            ),
            "CDS hips2fits (DSS images)": lambda: overlays.dss_image(83.82, -5.39, 0.1, 64)[0].shape,
            "IRSA ZTF light curves": lambda: f"{len(surveys.ztf(SkyCoord(285.6 * u.deg, 30.5 * u.deg)))} points",
            "AAVSO International Database": lambda: (
                f"{len(surveys.aavso('SS Cyg', from_jd=2460600, to_jd=2460620))} points"
            ),
            "MAST (TESS / Kepler)": mast,
            "PHOENIX spectra (stellar parameters)": lambda: _head(atmosphere.PHOENIX),
            "Kurucz solar atlas": lambda: _head(atmosphere.KURUCZ_SUN),
            "Pickles templates (spectral types)": lambda: _head(templates.PICKLES_URL.format(i=1)),
            "IERS Earth orientation": iers,
        }
    )


def report(results):
    width = max(len(n) for n, _, _ in results)
    lines = [f"{'OK  ' if ok else 'FAIL'}  {name:<{width}}  {detail}" for name, ok, detail in results]
    return "\n".join(lines)
