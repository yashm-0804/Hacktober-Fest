#!/usr/bin/env bash
# Build the AushNexa web app and serve it, together with the API, at http://localhost:8000.
#
#   ./run-website.sh            build, set up the backend if needed, start the server and open the browser
#   ./run-website.sh --warm     also warm the Gemma cache for the demo case first (needs GEMINI_API_KEY)
#
# Stop it with Ctrl+C.
set -euo pipefail
cd "$(dirname "$0")"
PORT="${PORT:-8000}"

PY=""
for candidate in python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$candidate" >/dev/null && "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 10))'; then
    PY="$candidate"
    break
  fi
done
if [ -z "$PY" ]; then
  echo "Python 3.10 or newer is needed. On a Mac: brew install python@3.12" >&2
  exit 1
fi
if ! command -v npm >/dev/null; then
  echo "Node.js is needed. On a Mac: brew install node" >&2
  exit 1
fi

echo "==> Building the web app"
(cd mobile && npm install --no-fund --no-audit && npx expo export --platform web)

echo "==> Setting up the backend"
cd backend
[ -x .venv/bin/python ] || "$PY" -m venv .venv
.venv/bin/python -m pip --version >/dev/null 2>&1 || .venv/bin/python -m ensurepip >/dev/null
.venv/bin/python -m pip install -q -r requirements.txt
[ -f .env ] || cp .env.example .env
if ! grep -qE '^GEMINI_API_KEY=.{30,}' .env; then
  echo "    Note: no Gemini API key in backend/.env (get one at https://aistudio.google.com/apikey)."
  echo "          Photos can't be read without it; typed prescriptions still work."
fi

if [ "${1:-}" = "--warm" ]; then
  echo "==> Warming the Gemma cache for the demo case (this can take a few minutes)"
  .venv/bin/python scripts/warm_cache.py || echo "    Some steps failed; the demo still works, just slower."
fi

URL="http://localhost:$PORT"
echo "==> AushNexa is running at $URL  (Ctrl+C to stop)"
if command -v open >/dev/null; then
  (sleep 3 && open "$URL") &
fi
exec .venv/bin/uvicorn api:app --host 0.0.0.0 --port "$PORT"
