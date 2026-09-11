# DepthWizard

DepthWizard turns aerial RGB imagery into an interactive estimated nDSM visualization.

## Local development

### Backend

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

Use the virtual-environment interpreter to start Uvicorn. On macOS, the system/Homebrew
Python may resolve a different PyTorch build and load a second `libomp.dylib`.

Place the fine-tuned checkpoint at the repository root as `astra.pth`, or point to it with
`DEPTHWIZARD_CHECKPOINT=/absolute/path/to/astra.pth`. The first real image upload also
downloads the base `depth-anything/Depth-Anything-V2-Small-hf` weights from Hugging Face and
caches them locally. The `Try a GAMUS example` action remains fixture-backed for fast UI checks.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in a browser. Uploaded PNG, JPEG, RGB GeoTIFF, and RGBA GeoTIFF
files use the fine-tuned model and render an estimated nDSM scene in meters. The frontend
reports whether the FastAPI health endpoint is reachable.

## Reconstruction modes

Live inference uses overlapping 518×518 tiles with 50% overlap, weighted blending, and
horizontal-flip test-time augmentation, so large images are reconstructed across their full
footprint. Model predictions are downsampled to a 256×256 scene grid. Building regions are
currently derived from the height map as a labeled fallback; the renderer turns them into
clean walls and inferred flat/gabled roofs while retaining a continuous terrain surface.
The optional RGB relief layer remains available for inspecting the original height-field mode.

The GAMUS semantic-head training path is not enabled by default in this checkout: it requires
the locally downloaded `classes/` data and a newly trained multitask checkpoint.
