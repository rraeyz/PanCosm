"""The command line without a window (plans/architecture.md ARC-12 item 2):

    astrowb-cli steps                              every step with one line of help
    astrowb-cli help photometry.light_curve        its inputs, parameters and defaults
    astrowb-cli run <step> key=value … [--project P] [--json] [--quiet]
    astrowb-cli recipe night.json [--set key=value …] [--project P] [--json]   (an automation file)

A value is read as JSON when it is JSON (3, 2.5, true, [1, 2], {"a": 1}), else as text; a key that is an input of
the step is an input, every other key must be one of its parameters. Exit codes: 0 done, 2 the command is wrong,
3 the step failed (its message is printed), 4 the program failed (the trace is printed and logged).
"""

import argparse
import json
import sys
import traceback

from .engine.tasks import TaskFailed

COMMANDS = ("steps", "help", "run", "recipe")
# errors that mean a fault in the program rather than in the data or the request
BUGS = {"TypeError", "AttributeError", "IndexError", "NameError", "ZeroDivisionError", "AssertionError",
        "UnboundLocalError", "RecursionError"}  # fmt: skip
USAGE, FAILED, CRASHED = 2, 3, 4


class UsageError(Exception):
    pass


def _value(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _pairs(items):
    out = {}
    for item in items:
        key, sep, value = item.partition("=")
        if not sep or not key:
            raise UsageError(f"expected key=value, got {item!r}")
        out[key] = _value(value)
    return out


def _summary(func, width=110):
    """The first paragraph of a step's docstring on one line, shortened to `width`."""
    text = " ".join((func.__doc__ or "").strip().split("\n\n")[0].split())
    return text if len(text) <= width else text[: width - 1].rsplit(" ", 1)[0] + " …"


def list_steps(out):
    from .engine import steps

    steps._load_builtin()
    width = max(len(s) for s in steps.REGISTRY)
    for sid in sorted(steps.REGISTRY):
        print(f"{sid:<{width}}  {_summary(steps.REGISTRY[sid].func)}", file=out)


def describe(step_id, out):
    from .engine import steps

    try:
        s = steps.get(step_id)
    except KeyError:
        raise UsageError(f"no step {step_id} (astrowb-cli steps lists them)") from None
    print(step_id, file=out)
    import inspect

    doc = inspect.cleandoc(s.func.__doc__ or "")  # the docstring's own indentation taken off
    if doc:
        print("\n" + doc, file=out)
    print("\ninputs:      " + (", ".join(s.inputs) or "none"), file=out)
    if s.optional:
        print("optional:    " + ", ".join(s.optional), file=out)
    print("outputs:     " + (", ".join(s.outputs) or "none"), file=out)
    if s.defaults:
        print("parameters (default):", file=out)
        for key, value in s.defaults.items():
            print(f"  {key} = {json.dumps(value)}", file=out)


def _split(step_id, values):
    from .engine import steps

    try:
        s = steps.get(step_id)
    except KeyError:
        raise UsageError(f"no step {step_id} (astrowb-cli steps lists them)") from None
    names = set(s.inputs) | set(s.optional)
    inputs = {k: v for k, v in values.items() if k in names}
    params = {k: v for k, v in values.items() if k not in names}
    unknown = sorted(set(params) - set(s.defaults))
    if unknown:
        raise UsageError(f"{step_id} has no input or parameter {', '.join(unknown)} (astrowb-cli help {step_id})")
    missing = sorted(set(s.inputs) - set(inputs))
    if missing:
        raise UsageError(f"{step_id} needs {', '.join(missing)}")
    return inputs, params


def _engine(project):
    from .engine.core import Engine
    from .engine.project import Project

    return Engine(Project(project) if project else None)


def _show(result, as_json, out):
    if as_json:
        print(json.dumps(result, indent=1, default=str), file=out)
    else:
        for key, value in result.items():
            print(f"{key}: {value}", file=out)


def main(argv, out=None, err=None):
    out, err = out or sys.stdout, err or sys.stderr  # looked up now: the streams may have been replaced
    parser = argparse.ArgumentParser(prog="astrowb-cli", description="Run steps without the window.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("steps", help="list every step")
    h = sub.add_parser("help", help="inputs, parameters and defaults of a step")
    h.add_argument("step")
    for name in ("run", "recipe"):
        p = sub.add_parser(name, help="run one step" if name == "run" else "run an automation file")
        p.add_argument("step" if name == "run" else "file")
        p.add_argument("values", nargs="*", metavar="key=value") if name == "run" else p.add_argument(
            "--set", nargs="*", default=[], metavar="key=value", help="the automation's inputs"
        )
        p.add_argument("--project", help="record the run in this project file (.astroproj)")
        p.add_argument("--json", action="store_true", help="print the outputs as JSON")
        p.add_argument("--quiet", action="store_true", help="no progress on stderr")
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code == 0 else USAGE
    engine = None
    try:
        if args.command == "steps":
            list_steps(out)
            return 0
        if args.command == "help":
            describe(args.step, out)
            return 0
        if args.command == "run":
            inputs, params = _split(args.step, _pairs(args.values))
            engine = _engine(args.project)
            if not args.quiet:
                print(f"running {args.step} …", file=err)
            result = engine.run_step(args.step, inputs, params).result()
        else:
            from .engine import automation

            auto = automation.load(args.file)
            engine = _engine(args.project)
            if not args.quiet:
                print(f"running {auto.get('name', args.file)} ({len(auto['steps'])} steps) …", file=err)
            result = automation.run(engine, auto, _pairs(args.set))
        _show(result, args.json, out)
        return 0
    except UsageError as e:
        print(f"astrowb-cli: {e}", file=err)
        return USAGE
    except TaskFailed as e:  # the step's own message (exit 3), or a fault in the program (exit 4, logged)
        from .ui.messages import task_error

        trace = str(e)
        message = task_error(trace)
        kind = message.partition(":")[0] if ":" in message.splitlines()[0] else ""
        print(f"failed: {message}", file=err)
        if kind in BUGS:
            _log(trace)
            return CRASHED
        return FAILED
    except (ValueError, OSError, KeyError) as e:  # before any step ran: an unreadable automation file and the like
        print(f"failed: {e}", file=err)
        return FAILED
    except Exception:  # noqa: BLE001 - every other failure is a crash: printed and logged for a report
        trace = traceback.format_exc()
        print(trace, file=err)
        _log(trace)
        return CRASHED
    finally:
        if engine is not None:
            engine.shutdown()


def _log(trace):
    from .settings import config_dir

    try:
        path = config_dir() / "error.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(trace + "\n")
    except OSError:
        pass
