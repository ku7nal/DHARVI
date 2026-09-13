#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -x "$ROOT_DIR/backend/.venv/bin/python" ]]; then
  echo "Missing backend virtual environment. See README.md for setup." >&2
  exit 1
fi
if [[ ! -d "$ROOT_DIR/frontend/node_modules" ]]; then
  echo "Missing frontend dependencies. Run: cd frontend && npm install" >&2
  exit 1
fi
echo "== Model checkpoint =="
"$ROOT_DIR/scripts/verify-model.sh"

echo "== Backend tests =="
(cd "$ROOT_DIR/backend" && .venv/bin/python -m unittest discover -s tests -p 'test_*.py')
echo "== Frontend checks =="
(cd "$ROOT_DIR/frontend" && npm run typecheck && npm run build && npm run test:scene && npm run test:buildings && npm run test:terrain && npm run test:quality)
echo "Deliverable verification passed."
