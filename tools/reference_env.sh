#!/usr/bin/env bash
# The reference programs the validation tables are made with (plans/validation.md VAL-2), each outside this
# repository's own environment; nothing of them is imported by the package or its tests.
#
#   tools/reference_env.sh iraf          IRAF 2.17 and its NOAO packages (Debian / Ubuntu: apt; root or sudo)
#   tools/reference_env.sh <pip name>    a Python program (lightkurve, batman-package, ellc, …) in its own venv
#                                        under ~/.cache/astrowb-reference/<name>; run its scripts with that python
#
# Each table's script is in tests/validation/scripts/<program>/ and writes the table and its manifest.
set -euo pipefail
program="${1:?usage: tools/reference_env.sh <program>}"
case "$program" in
  iraf)
    sudo=""; [ "$(id -u)" -ne 0 ] && sudo="sudo"
    $sudo apt-get install -y iraf iraf-noao
    echo "irafcl: $(command -v irafcl)" ;;
  *)
    home="${HOME}/.cache/astrowb-reference/${program}"
    python3 -m venv "$home"
    "$home/bin/pip" install --quiet "$program"
    echo "python for ${program}: $home/bin/python" ;;
esac
