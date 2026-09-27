# Reconstruction failure review

This review uses the existing `zaalima.jpeg` clear-building case and the supplied New York and Mexico City dense-city images with the current `dinosaur.pth` checkpoint. It is a visual diagnosis only: these images have no aligned reference raster, so the estimated nDSM values are not accuracy measurements.

Open [`index.html`](index.html) to compare input, predicted height, full-resolution semantics, scene-grid semantics, footprints, and the final application scene.

## Findings

- **Zaalima:** The height prediction is the first visible divergence. Large roof masses remain identifiable, but roof edges and smaller structures are smoothed before semantic labeling and extrusion.
- **New York:** The height preview retains broad structure and the semantic output recognizes the water boundary. The first clear divergence is semantic: building labels fragment and vegetation labels appear within developed blocks. Footprints and the scene carry those errors forward.
- **Mexico City:** The height map still responds to some rooftop structure, but the semantic mask labels 83.4% of scene-grid pixels as `others` and 2.4% as `building`; the resulting scene contains only 29 building regions.

The clear-building case first loses detail in the height prediction; both dense-city cases show their clearest failure in semantic classification. These observations are qualitative and do not establish measured accuracy.

## Recreate the prediction-stage artifacts

From the repository root, rerun inference on the included input copies:

```bash
HF_HUB_OFFLINE=1 PYTHONPATH=backend backend/.venv/bin/python -m training.reconstruction_failure_review \
  --checkpoint dinosaur.pth \
  --case zaalima-clear-buildings=.scratch/consistent-reconstruction-results/review/zaalima-clear-buildings/input.png \
  --case new-york=.scratch/consistent-reconstruction-results/review/new-york/input.png \
  --case mexico-city=.scratch/consistent-reconstruction-results/review/mexico-city/input.png \
  --finding 'zaalima-clear-buildings=The height prediction is the first visible divergence: large roof masses remain identifiable, but roof edges and smaller structures are smoothed before semantic labeling and extrusion.' \
  --finding 'new-york=Semantic labels are the first clear divergence after the height preview: water and broad structure remain visible, but building labels fragment and vegetation appears inside developed blocks.' \
  --finding 'mexico-city=Semantic labels are the first clear divergence after the height preview: 83.4% of scene-grid pixels are classified as others and only 2.4% as buildings, despite some rooftop structure remaining in the height prediction.' \
  --output .scratch/consistent-reconstruction-results/review
```

The command reuses the app’s model service, semantic cleanup, and footprint extractor. The first run may take a few minutes. `HF_HUB_OFFLINE=1` uses the already cached base model.

The `scene.png` files are screenshots from the running app after uploading the matching input. To refresh them, start the local app and run this in another terminal (with Playwright CLI and a browser installed):

```bash
playwright-cli open --browser webkit http://127.0.0.1:5173
playwright-cli run-code "async page => { for (const [name, file] of [['zaalima-clear-buildings', '.scratch/consistent-reconstruction-results/review/zaalima-clear-buildings/input.png'], ['new-york', '.scratch/consistent-reconstruction-results/review/new-york/input.png'], ['mexico-city', '.scratch/consistent-reconstruction-results/review/mexico-city/input.png']]) { await page.reload(); await page.locator('input[type=file]').waitFor({ state: 'attached' }); await page.locator('input[type=file]').setInputFiles(file); await page.getByText('Buildings:', { exact: false }).waitFor({ state: 'visible', timeout: 180000 }); await page.waitForTimeout(1500); await page.screenshot({ path: `.scratch/consistent-reconstruction-results/review/${name}/scene.png`, fullPage: true }); } return 'Scenes captured'; }"
```

Run the prediction command with `--report-only` and the same `--finding` values to rebuild the HTML after screenshot capture without repeating inference.
