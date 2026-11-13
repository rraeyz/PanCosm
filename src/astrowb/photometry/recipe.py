"""The Photometry window's measurement as a recipe (plans/photometry.md PHO-20): an automation file with the one
step photometry.light_curve, its inputs carried as values (the frames, the stars, the target's position) and its
parameters as the window set them. `astrowb-cli recipe night.json --set images='["a.fits", …]'` runs it again
without the window; any input can be replaced that way."""

from ..engine import automation

KINDS = {"images": "files", "target_xy": "xy", "comps_xy": "pairs", "coord": "text", "extra_xy": "pairs",
         "ref_image": "file"}  # fmt: skip


def light_curve_recipe(images, target_xy, comps_xy, params, coord="", extra_xy=(), ref_image=None, name="Light curve"):
    values = {"images": [str(p) for p in images], "target_xy": list(map(float, target_xy)),
              "comps_xy": [list(map(float, c)) for c in comps_xy]}  # fmt: skip
    if coord:
        values["coord"] = coord
    if extra_xy:
        values["extra_xy"] = [list(map(float, c)) for c in extra_xy]
    if ref_image:
        values["ref_image"] = str(ref_image)
    return {
        "name": {"en": name},
        "description": {"en": "Differential photometry as measured in the Photometry window."},
        "inputs": {k: {"kind": KINDS[k], "label": {"en": k}, "value": v} for k, v in values.items()},
        "steps": [{"step": "photometry.light_curve", "params": dict(params)}],
    }


def save(recipe, path):
    return automation.save(recipe, path)
