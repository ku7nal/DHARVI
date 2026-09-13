# DepthWizard

DepthWizard turns aerial RGB imagery into an interactive estimated nDSM visualization.

## Local development

### One-command local startup

After installing the dependencies below, start both services with:

```bash
./scripts/start-local.sh
```

The script uses `DEPTHWIZARD_CHECKPOINT` when set, otherwise `dinosaur.pth`. It checks the backend virtual environment, frontend dependencies, and checkpoint before starting FastAPI on port 8000 and Vite on port 5173. Run `./scripts/verify-deliverable.sh` for the complete pre-demo check.

### Backend

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

Use the virtual-environment interpreter to start Uvicorn. On macOS, the system/Homebrew
Python may resolve a different PyTorch build and load a second `libomp.dylib`.

Place the fine-tuned checkpoint at the repository root as `dinosaur.pth`, or point to it with
`DEPTHWIZARD_CHECKPOINT=/absolute/path/to/checkpoint.pth`. The first real image upload also
downloads the base `depth-anything/Depth-Anything-V2-Small-hf` weights from Hugging Face and
caches them locally. The `Try a GAMUS example` action remains fixture-backed for fast UI checks.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in a browser. Uploaded PNG, JPG/JPEG, RGB GeoTIFF, and RGBA GeoTIFF
files use the fine-tuned model and render an estimated nDSM scene in meters. The frontend
reports whether the FastAPI health endpoint is reachable.

Uploads are limited to 256 MB by default. Set `DEPTHWIZARD_MAX_UPLOAD_BYTES` for a controlled
offline demo with a different limit.

## Reconstruction modes

Live inference uses overlapping 518×518 tiles with 50% overlap, weighted blending, and
horizontal-flip test-time augmentation, so large images are reconstructed across their full
footprint. Model predictions are downsampled to a 256×256 scene grid. Building regions are
currently derived from the height map as a labeled fallback; the renderer turns them into
clean walls and inferred flat/gabled roofs while retaining a continuous terrain surface.
The optional RGB relief layer remains available for inspecting the original height-field mode.

The GAMUS semantic-head training path is not enabled by default in this checkout: it requires
the locally downloaded `classes/` data and a newly trained multitask checkpoint.

## GAMUS multitask training

After downloading GAMUS into a directory containing `images/`, `heights/`, and `classes/`,
run the reproducible training/evaluation path from the backend environment:

```bash
cd backend
.venv/bin/python -m training.gamus_multitask /data/gamus \
  --baseline-checkpoint /absolute/path/to/checkpoint.pth \
  --output checkpoints/gamus_multitask.pth \
  --validation-group Philadelphia
```

The loader rejects spatially mismatched triplets and ambiguous RGB class masks without an
explicit palette. Splits are geographic groups rather than random tiles. Validation uses
overlapping full-image inference and reports height RMSE/MAE/correlation, semantic mIoU,
building F1, and building-boundary F1. The multitask checkpoint is saved separately and
records the baseline checkpoint and baseline height metrics used for initialization.
