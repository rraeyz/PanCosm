"""photometry.tesscut: TESS full-frame-image cut-outs of a target from MAST (PHO-32)."""

from ..engine.params import QT_TRANSLATE_NOOP, P
from ..engine.steps import step


@step(
    "photometry.tesscut",
    inputs=("target", "cache"),
    outputs=("images", "sectors"),
    params=(
        P(
            "size",
            "int",
            15,
            unit="px",
            min=1,
            label=QT_TRANSLATE_NOOP("Steps", "Cut-out size"),
            help=QT_TRANSLATE_NOOP("Steps", "Side of the square cut out of the full-frame images, in TESS pixels"),
        ),
        P(
            "sector",
            "int",
            0,
            min=0,
            label=QT_TRANSLATE_NOOP("Steps", "Sector"),
            help=QT_TRANSLATE_NOOP("Steps", "0: every sector that observed the target"),
        ),
    ),
)
def tesscut_step(inputs, params, ctx):
    """TESScut cut-outs around a target (name or 'RA Dec'), one pixel file per sector (needs the internet)."""
    from ..services import mast

    target = str(inputs["target"]).strip()
    if not target:
        raise ValueError("give the target's name or coordinates")
    ctx.progress(0.05, "MAST")
    sectors = mast.tess_sectors(target)
    ctx.check()
    ctx.progress(0.2, "MAST")  # a name, the same in every language
    return {"images": mast.tess_cutout(target, inputs["cache"], params["size"], params["sector"]), "sectors": sectors}
