#!/usr/bin/env bash
# Bootstrap a virtualenv on first run, then hand off to pytest.
#
#   ./tests/run.sh                        run everything, in parallel
#   ./tests/run.sh -k swipe               run matching tests
#   ./tests/run.sh -p no:xdist            run serially, for readable output
#   ./tests/run.sh --headed --slowmo 400  watch it in a real window
#
# Starts a Jekyll server if nothing is answering, and builds the site once with
# the production config. Doing both here rather than in a fixture means the
# parallel workers share them instead of racing to create their own.
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

BASE_URL="${BASE_URL:-http://localhost:4000}"
export BASE_URL

started_server=""
if ! curl -sf -o /dev/null --max-time 3 "$BASE_URL"; then
	echo "nothing on $BASE_URL, starting jekyll ..."
	(cd .. && bundle exec jekyll serve --quiet >/dev/null 2>&1 &)
	started_server="yes"
	for _ in $(seq 1 90); do
		curl -sf -o /dev/null --max-time 3 "$BASE_URL" && break
		sleep 2
	done
fi

# One production build for the tests that check absolute URLs. _site is no use
# to them: `jekyll serve` keeps rewriting it with site.url on localhost.
PRODUCTION_SITE="$(mktemp -d)"
export PRODUCTION_SITE
(cd .. && bundle exec jekyll build --quiet --destination "$PRODUCTION_SITE")

cleanup() {
	rm -rf "$PRODUCTION_SITE"
	[ -n "$started_server" ] && pkill -f "jekyll serve" >/dev/null 2>&1 || true
}
trap cleanup EXIT

exec "$VENV/bin/python" -m pytest "$@"
