"""Size limits of modules and functions (plans/architecture.md "Code rules", ARC-4.1).

    python tools/module_sizes.py            -> list everything over a limit; exit 1 if something new is over
    python tools/module_sizes.py --update   -> write today's oversized files and functions into the allow-list

Limits: an interface module (ui/) at most 700 lines, any other module at most 900, a function at most 80 lines.
Files and functions that were over a limit before the rule are on the allow-list below with the size they had;
they may shrink but not grow (a ratchet). ARC-4 removes them from the list one by one.
"""

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "astrowb"
ALLOW = ROOT / "tools" / "module_sizes_allow.json"
UI_LIMIT, MODULE_LIMIT, FUNCTION_LIMIT = 700, 900, 80


def measure():
    """({relative path: lines} over the module limit, {"path:qualname": lines} over the function limit)."""
    files, functions = {}, {}
    for path in sorted(SRC.rglob("*.py")):
        rel = path.relative_to(SRC).as_posix()
        text = path.read_text(encoding="utf-8")
        lines = text.count("\n") + 1
        if lines > (UI_LIMIT if rel.startswith("ui/") else MODULE_LIMIT):
            files[rel] = lines

        def visit(node, prefix="", rel=rel):
            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                    name = f"{prefix}{child.name}"
                    if not isinstance(child, ast.ClassDef):
                        n = child.end_lineno - child.lineno + 1
                        if n > FUNCTION_LIMIT:
                            functions[f"{rel}:{name}"] = n
                    visit(child, name + ".", rel)

        visit(ast.parse(text))
    return files, functions


def problems():
    allow = json.loads(ALLOW.read_text(encoding="utf-8")) if ALLOW.exists() else {"files": {}, "functions": {}}
    files, functions = measure()
    out = []
    for kind, found in (("files", files), ("functions", functions)):
        for key, n in found.items():
            limit = allow[kind].get(key)
            if limit is None:
                out.append(f"{key}: {n} lines, over the limit (split it before adding to it)")
            elif n > limit:
                out.append(f"{key}: {n} lines, grew beyond its allowed {limit} (split it, do not add to it)")
    return out


def update():
    files, functions = measure()
    ALLOW.write_text(json.dumps({"files": files, "functions": functions}, indent=1, sort_keys=True) + "\n")
    print(f"{len(files)} files and {len(functions)} functions on the allow-list")


if __name__ == "__main__":
    if sys.argv[1:] == ["--update"]:
        update()
    else:
        found = problems()
        print("\n".join(found) or "all modules and functions within their limits")
        sys.exit(1 if found else 0)
