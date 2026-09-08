# DepthWizard

DepthWizard turns aerial RGB imagery into an interactive estimated nDSM visualization.

## Local development

### Backend

```bash
cd backend
python3 -m pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload --port 8000
```

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
