"""The Photometry window's measurement as a recipe (plans/photometry.md PHO-20): an automation file with the one
step photometry.light_curve, its inputs carried as values (the frames, the stars, the target's position) and its
parameters as the window set them. `astrowb-cli recipe night.json --set images='["a.fits", …]'` runs it again
without the window; any input can be replaced that way."""

from ..engine import automation

KINDS = {"images": "files", "target_xy": "xy", "comps_xy": "pairs", "coord": "text", "extra_xy": "pairs",
         "ref_image": "file", "stars_sky": "object"}  # fmt: skip


def light_curve_recipe(images, target_xy, comps_xy, params, coord="", extra_xy=(), ref_image=None, name="Light curve",
                       stars_sky=None):  # fmt: skip
    values = {"images": [str(p) for p in images], "target_xy": list(map(float, target_xy)),
              "comps_xy": [list(map(float, c)) for c in comps_xy]}  # fmt: skip
    if coord:
        values["coord"] = coord
    if extra_xy:
        values["extra_xy"] = [list(map(float, c)) for c in extra_xy]
    if ref_image:
        values["ref_image"] = str(ref_image)
    if stars_sky:  # another night's frames: the stars found by the sky (placed_by_sky)
        values["stars_sky"] = stars_sky
    return {
        "name": {"en": name},
        "description": {"en": "Differential photometry as measured in the Photometry window."},
        "inputs": {k: {"kind": KINDS[k], "label": {"en": k}, "value": v} for k, v in values.items()},
        "steps": [{"step": "photometry.light_curve", "params": dict(params)}],
    }


def save(recipe, path):
    return automation.save(recipe, path)


def placed_by_sky(inputs, images, ref):
    """A recipe run on another night (PHO-20): with "stars_sky" ({"target": [ra, dec], "comps": [[ra, dec], …],
    "extra": [[ra, dec], …]}), frames that are not the night they were marked on (ref_image not among them) and a
    plate-solved first frame, the stars are placed by the sky on it. Otherwise the inputs as given."""
    sky = inputs.get("stars_sky")
    if not sky or (inputs.get("ref_image") and str(ref) in map(str, images)):
        return inputs  # the night the stars were marked on: its pixels are exact
    from astropy.wcs import WCS

    from ..calibration.masters import load

    wcs = WCS(load(images[0])[1]).celestial
    if not wcs.has_celestial:
        return inputs

    def px(radec):
        return [float(v) for v in wcs.world_to_pixel_values(*radec)]

    out = dict(inputs) | {"target_xy": px(sky["target"]), "comps_xy": [px(c) for c in sky["comps"]],
                          "ref_image": images[0]}  # fmt: skip
    if sky.get("extra"):
        out["extra_xy"] = [px(c) for c in sky["extra"]]
    return out
