#!/usr/bin/env bash
# Bootstrap a virtualenv on first run, then hand off to pytest.
#
#   ./tests/run.sh                      run everything
#   ./tests/run.sh -k swipe             run matching tests
#   ./tests/run.sh --headed --slowmo 400  watch it in a real window
#
# Uses a Jekyll server on http://localhost:4000 if one is already running,
# otherwise starts and stops one itself.
set -euo pipefail
cd "$(dirname "$0")"

VENV=".venv"
if [ ! -x "$VENV/bin/pytest" ]; then
	echo "setting up $PWD/$VENV ..."
	python3 -m venv "$VENV"
	"$VENV/bin/pip" install --quiet --upgrade pip
	"$VENV/bin/pip" install --quiet -r requirements.txt
	"$VENV/bin/playwright" install chromium
fi

exec "$VENV/bin/python" -m pytest "$@"
