#!/bin/sh
# Same checks as CI's test job, run before every commit: sh tools/precommit.sh
set -e
ruff check .
ruff format --check .
python tools/check_brand.py
python tools/i18n.py >/dev/null
pytest -q
