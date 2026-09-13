# Hackathon deliverable guide

This is the demo-day handoff for DepthWizard: the reproducible local package, supported evidence paths, and final presentation checklist.

## Startup

From the repository root:

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cd ../frontend
npm install
cd ..
DEPTHWIZARD_CHECKPOINT="$PWD/dinosaur.pth" ./scripts/start-local.sh
```

Open `http://127.0.0.1:5173`. The startup script refuses to run if the checkpoint, backend environment, or frontend dependencies are missing. Use `DEPTHWIZARD_CHECKPOINT=/absolute/path/to/checkpoint.pth` for another checkpoint.

Before presenting, run `./scripts/verify-deliverable.sh`. It verifies the serialized checkpoint and GAMUS taxonomy, then exercises upload failures, large-image tiling, calibration/export, semantic overlays, benchmark assets, and frontend scene checks through the automated test suite.

## Demo flow

1. Open **New reconstruction** and use the GAMUS fixture to show a deterministic seven-class semantic/building scene.
2. Upload a PNG or JPG to show relative nDSM output. These results are not absolute elevation measurements.
3. Upload an RGB or RGBA GeoTIFF with CRS metadata and provide ground elevation or valid ground-control points to enable the downloadable metric DSM GeoTIFF.
4. In the inspector, show building/semantic overlays, height inspection, slope heatmap, and orbit/top-down/fly navigation. Trees are disabled by default for performance.
5. Open **Examples** and switch between urban, sparse, hilly, and forested comparison groups. The current non-urban groups are synthetic stress fixtures, not held-out survey validation.

## Evidence and limitations

The validation workspace reports RMSE, MAE, correlation, semantic mIoU, building IoU, and building-boundary F1 with input/reference/prediction/error previews. See [landscape validation](validation/landscape-validation.md) for evidence status, failure cases, and dataset coverage limits. The checked-in groups are deterministic scaffold/stress results, not held-out survey evaluation.

Metric DSM claims require a georeferenced RGB GeoTIFF, a CRS and affine transform, sufficient ground evidence, and a successful `calibrated` response with a downloadable DSM. Missing CRS, insufficient ground pixels, invalid control points, or invalid spatial metadata are surfaced as explicit calibration statuses rather than silently exported as metric data.

## Final presentation checklist

- [ ] `./scripts/verify-deliverable.sh` passes on the demo machine.
- [ ] `./scripts/start-local.sh` starts both services with the intended checkpoint.
- [ ] `/api/health` returns `status: ok` before opening the UI.
- [ ] The PNG/JPG path is described as relative estimated nDSM.
- [ ] The GeoTIFF path demonstrates CRS metadata, calibration confidence, residual error, and DSM download.
- [ ] The large-image path has been checked with a representative 1024px-or-larger image.
- [ ] The scene demo shows fly, orbit, and top-down navigation plus height/slope inspection.
- [ ] Semantic/building overlays and bounded tree rendering are shown.
- [ ] Benchmark screenshots include all four landscape groups and the scaffold/metric evidence label.
- [ ] The presentation names GAMUS as urban-focused and calls out hilly, forested, sparse, canopy, occlusion, and relative-height limitations.
