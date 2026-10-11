"""The design system's colours as data (plans/interface.md "Colour tokens", UI-1): the one place a colour is written.
Everything else asks by name: `tokens.theme("dark")["text.muted"]`, `tokens.ROLES["comparison"]`,
`tokens.filter_colour("V")`.

NIGHT (red on black, for the dome at night) is prepared but not offered until the owner says so (interface.md
"To ask the owner").
"""

DARK = {
    "surface.0": "#14171c",  # window background
    "surface.1": "#1b1f26",  # panels, inputs, tables
    "surface.2": "#242a33",  # raised: buttons, headers, cards
    "surface.3": "#2d3440",  # hover
    "border": "#343c49",
    "border.strong": "#465062",
    "text": "#e7eaf0",
    "text.muted": "#9aa3b2",
    "text.faint": "#6b7485",
    "accent": "#4f8cff",
    "accent.hover": "#6ea0ff",
    "accent.pressed": "#3b74e0",
    "on.accent": "#ffffff",
    "ok": "#3ecf8e",
    "attention": "#f5a524",
    "error": "#f0544f",
    "image.background": "#000000",
}
LIGHT = {
    "surface.0": "#f4f6f9",
    "surface.1": "#ffffff",
    "surface.2": "#eef1f5",
    "surface.3": "#e3e8ef",
    "border": "#d3d9e2",
    "border.strong": "#b6bfcc",
    "text": "#1a2130",
    "text.muted": "#5b6576",
    "text.faint": "#8a93a3",
    "accent": "#2f6fe4",
    "accent.hover": "#4a83ea",
    "accent.pressed": "#2459c2",
    "on.accent": "#ffffff",
    "ok": "#1f9d63",
    "attention": "#b7791f",
    "error": "#d1343f",
    "image.background": "#000000",
}
NIGHT = {  # dark-adapted eyes: every colour a red of some brightness
    **{k: "#000000" for k in ("surface.0", "image.background")},
    "surface.1": "#0d0000",
    "surface.2": "#1a0000",
    "surface.3": "#260000",
    "border": "#330000",
    "border.strong": "#4d0000",
    "text": "#ff3b30",
    "text.muted": "#b32a22",
    "text.faint": "#801e18",
    "accent": "#ff3b30",
    "accent.hover": "#ff5a50",
    "accent.pressed": "#cc2f26",
    "on.accent": "#000000",
    "ok": "#ff3b30",
    "attention": "#ff3b30",
    "error": "#ff3b30",
}
THEMES = {"dark": DARK, "light": LIGHT}  # offered; "night" is loaded as dark until it is offered
DEFAULT = "dark"

# data roles, the same in images, plots and tables (Okabe–Ito based: red–green colour blindness keeps them apart)
ROLES = {
    "target": "#00b386",
    "comparison": "#e8642c",
    "check": "#56b4e9",
    "suggested": "#c8ccd4",
    "rejected": "#6b7485",
    "non_linear": "#f5a524",
    "saturated": "#f0544f",
}
SERIES = ("#4f8cff", "#e69f00", "#00b386", "#e8642c", "#cc79a7", "#56b4e9", "#f0e442")  # then text.muted
FILTERS = {
    "U": "#7b5cd6", "B": "#4f7dff", "V": "#3aa657", "R": "#e5484d", "I": "#a23b3b",
    "u'": "#6f52c9", "g'": "#2fa8a0", "r'": "#e5674d", "i'": "#b0413e", "z'": "#7a2e2e",
    "clear": "#9aa3b2", "TESS": "#c2410c", "Kepler": "#b45309", "G": "#6aa84f", "BP": "#4f7dff", "RP": "#e5484d",
}  # fmt: skip
_FILTER_NAMES = {"u′": "u'", "g′": "g'", "r′": "r'", "i′": "i'", "z′": "z'", "SG": "g'", "SR": "r'", "SI": "i'",
                 "L": "clear", "CLEAR": "clear", "LUM": "clear", "CV": "clear", "Gaia G": "G"}  # fmt: skip


def theme(name):
    """The token table of a theme; an unknown or not yet offered name (an old "night") gives the default."""
    return THEMES.get(name, THEMES[DEFAULT])


def role(name):
    return ROLES[name]


def filter_colour(name, default=None):
    """The fixed colour of a filter as headers write it (V, Rc, SG, r′, TESS…), or default."""
    key = str(name or "").strip()
    key = _FILTER_NAMES.get(key, _FILTER_NAMES.get(key.upper(), key))
    if key not in FILTERS and key[:1].upper() in "UBVRI" and len(key) <= 2:  # Johnson–Cousins variants: Rc, Ic, Bj
        key = key[:1].upper()
    return FILTERS.get(key, default)


def contrast(fg, bg):
    """WCAG 2 contrast ratio of two #rrggbb colours (1 to 21)."""

    def luminance(c):
        rgb = [int(c[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        lin = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in rgb]
        return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]

    a, b = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (a + 0.05) / (b + 0.05)
