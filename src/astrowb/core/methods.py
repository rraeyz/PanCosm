"""The methods paragraphs of a project's recorded runs (plans/architecture.md ARC-11 item 4, the engine side): one
template per step in resources/methods/<step>.txt, filled with the run's recorded parameters; a step without a
template says nothing. English only, as a paper is."""

from pathlib import Path

from ..brand import BRAND
from ..engine.steps import REGISTRY, get

DIR = Path(__file__).resolve().parent.parent / "resources" / "methods"


def _extra(step_id, p):
    """Parts of a sentence that depend on a flag; they join the parameters the template can use."""
    if step_id == "calibration.run":
        return {
            "flat_clause": " and flat field" if p.get("divide_flat", True) else "",
            "cosmic_clause": ", and cosmic rays were removed with L.A.Cosmic" if p.get("cosmic_rays") else "",
        }
    return {}


def methods(runs):
    """Paragraph for the successful runs (Project.runs() dicts, in order); a step repeated gives one sentence per run
    only when its parameters differ."""
    seen, out = set(), []
    for r in runs:
        template = DIR / f"{r['step']}.txt"
        if r.get("status") != "done" or not template.is_file():
            continue
        get(r["step"])  # loads the built-in steps
        p = REGISTRY[r["step"]].defaults | (r.get("params") or {})
        version = (r.get("environment") or {}).get("app", "")
        text = (
            template.read_text(encoding="utf-8")
            .strip()
            .format_map({**p, **_extra(r["step"], p), "software": BRAND.display_name, "version": version})
        )
        if text not in seen:
            seen.add(text)
            out.append(text)
    return " ".join(out)
