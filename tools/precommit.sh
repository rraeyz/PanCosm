#!/bin/sh
# Same checks as CI's test job, run before every commit: sh tools/precommit.sh
set -e
ruff check .
ruff format --check .
python tools/check_brand.py
python tools/module_sizes.py
python tools/i18n.py >/dev/null
# all tests on every core; the ten slowest are printed so that a test that grew slow is seen (ARC-2).
# Quick loop while working: pytest -q -n auto -m "not slow"
pytest -q -n auto --durations=10
