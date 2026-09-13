#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHECKPOINT_INPUT="${1:-${DEPTHWIZARD_CHECKPOINT:-$ROOT_DIR/dinosaur.pth}}"
if [[ "$CHECKPOINT_INPUT" = /* ]]; then
  CHECKPOINT_PATH="$CHECKPOINT_INPUT"
else
  CHECKPOINT_PATH="$ROOT_DIR/$CHECKPOINT_INPUT"
fi
if [[ ! -f "$CHECKPOINT_PATH" ]]; then
  echo "Missing model checkpoint: $CHECKPOINT_PATH" >&2
  exit 1
fi

(cd "$ROOT_DIR/backend" && CHECKPOINT_PATH="$CHECKPOINT_PATH" .venv/bin/python - <<'PY'
import os
from pathlib import Path

import torch

from app.semantic_contract import CLASS_NAMES

path = Path(os.environ["CHECKPOINT_PATH"])
checkpoint = torch.load(path, map_location="cpu", weights_only=False)
if not isinstance(checkpoint, dict) or not isinstance(checkpoint.get("state_dict"), dict):
    raise SystemExit("Checkpoint must contain a state_dict mapping.")
classes = tuple(checkpoint.get("class_names", ()))
if classes != CLASS_NAMES:
    raise SystemExit(f"Checkpoint taxonomy mismatch: expected {CLASS_NAMES}, got {classes}.")
if not checkpoint.get("model_id"):
    raise SystemExit("Checkpoint is missing model_id metadata.")
print(f"Checkpoint verified: {path.name} · {checkpoint['model_id']} · {len(checkpoint['state_dict'])} tensors · GAMUS classes 0..6")
PY
)
