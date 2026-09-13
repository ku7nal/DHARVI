#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHECKPOINT_INPUT="${DEPTHWIZARD_CHECKPOINT:-$ROOT_DIR/dinosaur.pth}"
if [[ "$CHECKPOINT_INPUT" = /* ]]; then
  CHECKPOINT_PATH="$CHECKPOINT_INPUT"
else
  CHECKPOINT_PATH="$ROOT_DIR/$CHECKPOINT_INPUT"
fi
BACKEND_PYTHON="$ROOT_DIR/backend/.venv/bin/python"

if [[ ! -x "$BACKEND_PYTHON" ]]; then
  echo "Missing backend virtual environment: $BACKEND_PYTHON" >&2
  echo "Run: cd backend && python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt" >&2
  exit 1
fi
if [[ ! -f "$CHECKPOINT_PATH" ]]; then
  echo "Missing model checkpoint: $CHECKPOINT_PATH" >&2
  echo "Set DEPTHWIZARD_CHECKPOINT to a downloaded DepthWizard checkpoint." >&2
  exit 1
fi
if [[ ! -d "$ROOT_DIR/frontend/node_modules" ]]; then
  echo "Missing frontend dependencies: $ROOT_DIR/frontend/node_modules" >&2
  echo "Run: cd frontend && npm install" >&2
  exit 1
fi

cleanup() {
  trap - TERM INT EXIT
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup TERM INT EXIT

(
  cd "$ROOT_DIR/backend"
  DEPTHWIZARD_CHECKPOINT="$CHECKPOINT_PATH" "$BACKEND_PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port "${DEPTHWIZARD_API_PORT:-8000}"
) &
BACKEND_PID=$!
(
  cd "$ROOT_DIR/frontend"
  npm run dev -- --host 127.0.0.1 --port "${DEPTHWIZARD_UI_PORT:-5173}"
) &
FRONTEND_PID=$!

echo "DepthWizard API: http://127.0.0.1:${DEPTHWIZARD_API_PORT:-8000}"
echo "DepthWizard UI:  http://127.0.0.1:${DEPTHWIZARD_UI_PORT:-5173}"
wait "$BACKEND_PID" "$FRONTEND_PID"
