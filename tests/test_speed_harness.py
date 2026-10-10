"""ARC-23: the speed check flags a case that became slower, and not the noise of very short cases."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "tools"))
import speed  # noqa: E402


def doc(**seconds):
    return {"cases": {k: {"seconds": v} for k, v in seconds.items()}}


def test_a_slowed_case_fails_and_short_noise_does_not():
    base = doc(stack=2.0, period=0.5, tiny=0.01)
    assert speed.slower(base, doc(stack=2.9, period=0.6, tiny=0.05)) == []  # 1.45x; tiny is 5x but under 0.2 s
    assert [c for c, *_ in speed.slower(base, doc(stack=3.1, period=0.6, tiny=0.01))] == ["stack"]
    assert speed.compare(base, doc(stack=1.0))[0][3] == 0.5  # only the cases both have


def test_check_command_exit_code(tmp_path):
    import json

    a, b = tmp_path / "a.json", tmp_path / "b.json"
    a.write_text(json.dumps(doc(stack=2.0)))
    b.write_text(json.dumps(doc(stack=4.0)))
    assert speed.main(["check", str(a), str(b)]) == 1
    assert speed.main(["check", str(a), str(a)]) == 0
