"""The settings of the image, planning, models, remote-sensing and astrometry steps described (plans/automation.md
AUT-1.4 … 1.8): kind, unit, range, label, help. Imported once every step is registered (engine/builtin.py)."""

from . import builtin as _builtin  # noqa: F401  (every step first, whichever module is imported first)
from .params import QT_TRANSLATE_NOOP, P
from .steps import describe

describe(
    "planning.night",
    P(
        "min_alt",
        "float",
        20.0,
        unit="°",
        min=0.0,
        max=90.0,
        label=QT_TRANSLATE_NOOP("Steps", "Lowest altitude"),
        help=QT_TRANSLATE_NOOP("Steps", "A target lower than this is not observable"),
    ),
    P(
        "step_min",
        "float",
        5.0,
        unit="min",
        min=0.1,
        label=QT_TRANSLATE_NOOP("Steps", "Time step"),
        help=QT_TRANSLATE_NOOP("Steps", "The night is computed at this spacing"),
    ),
)
describe(
    "planning.ephemeris",
    P(
        "catalogue",
        "text",
        "auto",
        label=QT_TRANSLATE_NOOP("Steps", "Catalogue"),
        help=QT_TRANSLATE_NOOP("Steps", "auto: VSX for variable stars, the NASA Exoplanet Archive for planets"),
    ),
)
describe("rs.classify", P("k", "int", 5, min=2, max=50, label=QT_TRANSLATE_NOOP("Steps", "Classes"),
                          help=QT_TRANSLATE_NOOP("Steps", "How many k-means classes")))  # fmt: skip
describe("rs.pca", P("n", "int", 3, min=1, max=50, label=QT_TRANSLATE_NOOP("Steps", "Components"),
                     help=QT_TRANSLATE_NOOP("Steps", "How many principal components are kept")))  # fmt: skip
describe(
    "models.visual_orbit",
    P(
        "p_min",
        "float",
        None,
        unit="yr",
        min=0.0,
        label=QT_TRANSLATE_NOOP("Steps", "Shortest period"),
        help=QT_TRANSLATE_NOOP("Steps", "With the longest: the search stays inside; empty: free"),
    ),
    P(
        "p_max",
        "float",
        None,
        unit="yr",
        min=0.0,
        label=QT_TRANSLATE_NOOP("Steps", "Longest period"),
        help=QT_TRANSLATE_NOOP("Steps", "With the shortest: the search stays inside; empty: free"),
    ),
    P(
        "parallax_mas",
        "float",
        None,
        unit="mas",
        min=0.0,
        label=QT_TRANSLATE_NOOP("Steps", "Parallax"),
        help=QT_TRANSLATE_NOOP("Steps", "Gives the total mass; empty: none"),
    ),
)
describe(
    "models.eb_fit",
    P(
        "free",
        "object",
        None,
        label=QT_TRANSLATE_NOOP("Steps", "Free parameters"),
        advanced=True,
        help=QT_TRANSLATE_NOOP("Steps", "The model's parameters that are fitted; empty: the usual set"),
    ),
    P(
        "ld1",
        "table",
        (0.0, 0.0),
        label=QT_TRANSLATE_NOOP("Steps", "Limb darkening, star 1"),
        help=QT_TRANSLATE_NOOP("Steps", "Quadratic coefficients u1, u2"),
    ),
    P(
        "ld2",
        "table",
        (0.0, 0.0),
        label=QT_TRANSLATE_NOOP("Steps", "Limb darkening, star 2"),
        help=QT_TRANSLATE_NOOP("Steps", "Quadratic coefficients u1, u2"),
    ),
    P(
        "mcmc_steps",
        "int",
        0,
        min=0,
        max=1_000_000,
        label=QT_TRANSLATE_NOOP("Steps", "MCMC steps"),
        advanced=True,
        help=QT_TRANSLATE_NOOP(
            "Steps", "The most steps of the Markov chains for the errors (they stop earlier once converged); 0: none"
        ),
    ),
    P(
        "export_format",
        "choice",
        "phoebe",
        choices=("phoebe", "wd", "transit"),
        label=QT_TRANSLATE_NOOP("Steps", "Export for"),
        help=QT_TRANSLATE_NOOP("Steps", "PHOEBE, Wilson–Devinney or a transit-fitting program"),
    ),
)
describe(
    "astrometry.solve",
    P(
        "radius_deg",
        "float",
        30.0,
        unit="°",
        min=0.0,
        max=180.0,
        label=QT_TRANSLATE_NOOP("Steps", "Search radius"),
        help=QT_TRANSLATE_NOOP("Steps", "Around the header's position"),
    ),
    P(
        "refine_gaia",
        "bool",
        True,
        label=QT_TRANSLATE_NOOP("Steps", "Refine on Gaia"),
        help=QT_TRANSLATE_NOOP("Steps", "The solution is fitted again on Gaia DR3 stars (higher-order distortion)"),
    ),
)
describe(
    "astrometry.moving",
    P(
        "box",
        "int",
        11,
        unit="px",
        min=3,
        max=101,
        label=QT_TRANSLATE_NOOP("Steps", "Box"),
        help=QT_TRANSLATE_NOOP("Steps", "The object is looked for in a box this wide"),
    ),
)
describe(
    "image.catalogue",
    P(
        "catalogue",
        "text",
        "gaia",
        label=QT_TRANSLATE_NOOP("Steps", "Catalogue"),
        help=QT_TRANSLATE_NOOP(
            "Steps", "The stars shown over the image: gaia, vsx or aavso (the AAVSO comparison sequence)"
        ),
    ),
    P(
        "mag_limit",
        "float",
        16.0,
        unit="mag",
        label=QT_TRANSLATE_NOOP("Steps", "Faintest magnitude"),
        help=QT_TRANSLATE_NOOP("Steps", "Fainter stars are left out"),
    ),
)
describe(
    "image.convert",
    P(
        "fmt",
        "text",
        "png",
        label=QT_TRANSLATE_NOOP("Steps", "Format"),
        help=QT_TRANSLATE_NOOP("Steps", "png, jpg or tif"),
    ),
    P(
        "interval",
        "text",
        "zscale",
        label=QT_TRANSLATE_NOOP("Steps", "Levels"),
        help=QT_TRANSLATE_NOOP("Steps", "How the black and white points are chosen"),
    ),
    P(
        "stretch",
        "text",
        "linear",
        label=QT_TRANSLATE_NOOP("Steps", "Stretch"),
        help=QT_TRANSLATE_NOOP("Steps", "linear, log, sqrt, asinh…"),
    ),
)
describe(
    "image.finder_chart",
    P(
        "fov_deg",
        "float",
        0.3,
        unit="°",
        min=0.0,
        label=QT_TRANSLATE_NOOP("Steps", "Field of view"),
        help=QT_TRANSLATE_NOOP("Steps", "Width of the chart"),
    ),
    P(
        "mag_limit",
        "float",
        14.0,
        unit="mag",
        label=QT_TRANSLATE_NOOP("Steps", "Faintest magnitude"),
        help=QT_TRANSLATE_NOOP("Steps", "Fainter stars are left out"),
    ),
    P(
        "title",
        "text",
        "",
        label=QT_TRANSLATE_NOOP("Steps", "Title"),
        help=QT_TRANSLATE_NOOP("Steps", "Above the chart"),
    ),
)
describe("image.minor_planets", P("mag_limit", "float", 20.0, unit="mag",
                                  label=QT_TRANSLATE_NOOP("Steps", "Faintest magnitude"),
                                  help=QT_TRANSLATE_NOOP("Steps", "Fainter bodies are left out")))  # fmt: skip
describe("image.process", P("args", "object", {}, label=QT_TRANSLATE_NOOP("Steps", "Arguments"),
                            help=QT_TRANSLATE_NOOP("Steps", "The operation's own settings")))  # fmt: skip
describe(
    "image.rgb",
    P(
        "stretch",
        "float",
        0.5,
        min=0.0,
        label=QT_TRANSLATE_NOOP("Steps", "Stretch"),
        help=QT_TRANSLATE_NOOP("Steps", "Lupton's stretch"),
    ),
    P(
        "q",
        "float",
        8.0,
        min=0.0,
        label=QT_TRANSLATE_NOOP("Steps", "Softening"),
        help=QT_TRANSLATE_NOOP("Steps", "Lupton's Q"),
    ),
    P(
        "align",
        "bool",
        True,
        label=QT_TRANSLATE_NOOP("Steps", "Align"),
        help=QT_TRANSLATE_NOOP("Steps", "The three images are aligned on their stars first"),
    ),
)
describe(
    "fits.save_as",
    P(
        "overwrite",
        "bool",
        False,
        label=QT_TRANSLATE_NOOP("Steps", "Overwrite"),
        help=QT_TRANSLATE_NOOP("Steps", "An existing file of that name is replaced"),
    ),
    P(
        "set_cards",
        "object",
        {},
        label=QT_TRANSLATE_NOOP("Steps", "Header cards to set"),
        help=QT_TRANSLATE_NOOP("Steps", "Keyword: value pairs written into the header"),
    ),
    P(
        "delete",
        "table",
        [],
        label=QT_TRANSLATE_NOOP("Steps", "Header cards to delete"),
        help=QT_TRANSLATE_NOOP("Steps", "Keywords taken out of the header"),
    ),
)
