#!/bin/sh
# Real-data validation tests on this computer, as CI's validation job runs them (plans/architecture.md ARC-2).
#   sh tools/run_validation.sh            -> fetch what is missing into $ASTROWB_DATA (default ~/.cache/astrowb-data)
# The data are never put in the repository. Lesson of photometry item 9b: a change once passed every local test and
# broke the IRAF comparison in CI because the validation data were not present locally.
set -e
DATA="${ASTROWB_DATA:-$HOME/.cache/astrowb-data}"
mkdir -p "$DATA"
if [ ! -d "$DATA/EXOTIC_sampledata" ]; then
    echo "fetching the HAT-P-32 b night (EXOTIC sample data)"
    git clone --depth 1 https://github.com/rzellem/EXOTIC_sampledata "$DATA/EXOTIC_sampledata"
fi
ASTROWB_VALIDATION_DATA="$DATA/EXOTIC_sampledata" pytest -v tests/validation "$@"
