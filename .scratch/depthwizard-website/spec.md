# DepthWizard Website

Status: ready-for-agent

## Problem Statement

DepthWizard has a fine-tuned DepthAnything V2 Small model trained on the GAMUS dataset, but there is no usable product interface around it.

The current model produces estimated height-above-ground rasters that broadly capture buildings and vegetation, but users and judges need more than a raw prediction image. They need to upload aerial imagery, understand what the model produced, inspect accuracy where reference data exists, and explore the result as a clean interactive 3D scene.

The website must support ordinary RGB images as well as geospatially meaningful RGB/RGBA GeoTIFFs. It must preserve scientific honesty: arbitrary uploads do not have ground-truth accuracy metrics, and the model output must not be presented as absolute elevation above sea level.

## Solution

Build a minimal single-page workspace with a lavender application shell inspired by the provided reference design:

- A soft lavender/blue background.
- A centered white rounded application surface.
- A compact left navigation rail.
- A context-aware top bar.
- A dominant central 3D scene viewport.
- A collapsible right inspector for scene controls, layers, metadata, and metrics.

The primary workflow is:

```text
Upload → Processing → Stylized 3D result
                         ├── RGB preview
                         ├── estimated nDSM preview
                         ├── scene controls
                         └── analysis metadata
```

The backend exposes a stable prediction API. The initial implementation uses fixture results, allowing the frontend and 3D renderer to be built before model inference is connected. The fine-tuned DepthAnything V2 implementation is later inserted behind the same prediction service boundary.

The model result is labeled **Estimated nDSM (meters)** or **Estimated height above ground**. It is not labeled as absolute DSM unless a future SRTM-calibration workflow is implemented.

## User Stories

1. As a user, I want to open a clean reconstruction workspace, so that the product feels focused and understandable immediately.
2. As a user, I want to upload a PNG image, so that I can generate a reconstruction from a standard aerial image.
3. As a user, I want to upload a JPEG image, so that common aerial-image formats are supported.
4. As a user, I want to upload an RGB GeoTIFF, so that geospatial imagery can be processed.
5. As a user, I want to upload an RGBA GeoTIFF, so that imagery containing an alpha channel is accepted.
6. As a user, I want unsupported multispectral or non-RGB GeoTIFFs to be rejected clearly, so that I do not receive misleading predictions.
7. As a user, I want to drag and drop an image, so that uploading is quick and natural.
8. As a user, I want a normal file-picker action, so that I can upload files without drag and drop.
9. As a user, I want to try a built-in GAMUS example, so that I can understand the product without preparing an input file.
10. As a user, I want to see accepted formats before uploading, so that I know what the website supports.
11. As a user, I want the original uploaded image preserved for display, so that I can compare the input with the reconstruction.
12. As a user, I want the upload to enter a visible processing state, so that I know the request is still active.
13. As a user, I want processing failures to produce an understandable message, so that I know how to recover.
14. As a user, I want the first result to be the stylized 3D city, so that the product immediately communicates its main value.
15. As a user, I want to orbit around the scene, so that I can inspect the reconstruction from different angles.
16. As a user, I want to pan and zoom, so that I can inspect both the whole area and individual structures.
17. As a user, I want an isometric camera preset, so that the scene resembles the reference presentation.
18. As a user, I want to reset the camera, so that I can quickly return to the intended composition.
19. As a user, I want buildings to appear as clean extruded geometry, so that the result resembles a stylized 3D city rather than a noisy displaced plane.
20. As a user, I want the original RGB image available as a layer, so that I can compare the stylized scene with the source imagery.
21. As a user, I want the estimated nDSM surface available as a layer, so that I can inspect the raw height prediction.
22. As a user, I want a wireframe layer, so that I can understand the underlying scene geometry.
23. As a user, I want the stylized city layer to be the default, so that the main result is visually prominent.
24. As a user, I want to adjust height exaggeration, so that low-relief scenes remain visually legible.
25. As a user, I want true metric scale to remain the default, so that visual exploration does not silently change the scientific result.
26. As a user, I want the scene to render in local coordinates, so that interaction remains smooth and predictable.
27. As a GeoTIFF user, I want the original CRS preserved, so that the prediction remains associated with its geospatial reference.
28. As a GeoTIFF user, I want bounds and resolution displayed, so that I can understand the spatial scope of the input.
29. As a user, I want to see the estimated nDSM value range, so that I can understand the scale of the prediction.
30. As a user, I want the unit shown as meters, so that I do not confuse the output with generic monocular depth.
31. As a user, I want the model identity shown, so that I know which model produced the result.
32. As a user, I want the model’s GAMUS fine-tuning context shown, so that I understand the model’s expected domain.
33. As a user, I want arbitrary predictions to show diagnostics without invented accuracy scores, so that the product remains scientifically honest.
34. As a user, I want benchmark examples to show RMSE, so that I can assess large prediction errors.
35. As a user, I want benchmark examples to show MAE, so that I can assess average absolute error.
36. As a user, I want benchmark examples to show Pearson correlation, so that I can assess whether predicted and true height patterns agree.
37. As a user, I want benchmark examples to show the RGB input, so that I can connect the metrics to the source scene.
38. As a user, I want benchmark examples to show ground-truth LiDAR nDSM, so that I can compare the prediction to a reference.
39. As a user, I want benchmark examples to show an error map, so that I can locate where the model performs poorly.
40. As a user, I want the benchmark view to distinguish reference-backed metrics from diagnostics, so that I understand what is actually measured.
41. As a user, I want the app to explain that arbitrary uploads have no accuracy score without reference data, so that the limitation is clear.
42. As a user, I want the navigation to expose a New reconstruction action, so that I can start another input.
43. As a user, I want the navigation to expose Examples, so that I can inspect prepared benchmark scenes.
44. As a user, I want the navigation to expose About, so that I can read about the model, dataset, and limitations.
45. As a user, I want the top bar to show the current workspace title, so that I know which result I am viewing.
46. As a user, I want the top bar to show processing status, so that the current application state is visible.
47. As a user, I want the top bar to identify the model, so that the result has provenance.
48. As a user, I want a reset or new-reconstruction action in the top bar, so that I can quickly start over.
49. As a user, I want the right inspector to group controls into Scene, Layers, and Analysis, so that the interface remains easy to scan.
50. As a user, I want the right inspector sections collapsible, so that the 3D scene remains the dominant visual element.
51. As a user, I want the interface to use restrained borders, rounded controls, and subtle shadows, so that it feels polished without becoming visually noisy.
52. As a user, I want the first version to work locally on the demo machine, so that deployment infrastructure does not delay the hackathon demonstration.
53. As a developer, I want the frontend to consume a stable prediction response, so that model implementation changes do not require UI rewrites.
54. As a developer, I want the initial prediction endpoint to return fixtures, so that the website can be built before model inference is integrated.
55. As a developer, I want model inference isolated behind a prediction service, so that DepthAnything V2 can replace fixtures cleanly.
56. As a developer, I want the backend to preserve transform metadata, so that future full-resolution or tiled inference can be added without changing the public result model.
57. As a developer, I want synchronous processing in the first version, so that the request lifecycle remains simple for the demo.
58. As a developer, I want the API to expose health status, so that local development and troubleshooting are straightforward.

## Implementation Decisions

- Use a React and TypeScript frontend built with Vite.
- Use Three.js through React Three Fiber, with Drei for scene helpers and controls.
- Use a Python FastAPI backend with Pydantic response models.
- Use a single-page workspace with upload, processing, result, examples, and about states rather than a multi-page application.
- Use a stable prediction API as the highest integration seam between frontend and backend.
- Support PNG, JPEG, RGB GeoTIFF, and RGBA GeoTIFF inputs.
- Reject multispectral and non-RGB GeoTIFF inputs with a clear user-facing error.
- Preserve the original upload for display.
- Convert supported input to RGB for inference.
- For the first version, resize the shorter side to 518 pixels and center-crop to 518×518 for inference. Preserve the original image and transform metadata.
- Treat model output as estimated metric nDSM in meters because the training targets were GAMUS height-above-ground values in meters and the training loss directly optimized those values.
- Do not describe the model output as absolute DSM until an elevation-reference calibration workflow is implemented.
- Use the display labels “Estimated nDSM (meters)” and “Estimated height above ground.”
- Preserve GeoTIFF CRS, bounds, transform, and resolution in the result metadata.
- Render all scenes in a local coordinate system for interactive performance.
- Defer SRTM-based absolute DSM calibration.
- Use synchronous prediction requests for the first version, with visible loading and error states.
- Initially return fixture-backed results from the prediction service.
- Later load the fine-tuned DepthAnything V2 Small checkpoint behind the same prediction service.
- Reproduce the notebook’s inference assumptions: RGB input, ImageNet normalization, 518×518 model input, and non-negative output.
- Make the stylized 3D city the default result.
- Use orbit, pan, zoom, and isometric camera controls as the primary navigation model.
- Use true metric height scale by default, with a visual height-exaggeration control.
- Begin building extraction with a configurable height-threshold mask, morphology cleanup, connected-component filtering, and minimum-area filtering.
- Use neutral terrain for non-building surfaces in the first renderer. Do not claim road, water, or vegetation classifications without a semantic model.
- Keep scene layers for stylized city, estimated nDSM surface, RGB texture, and wireframe.
- Use a lavender/blue atmospheric background, centered white rounded application shell, left navigation, top bar, central scene viewport, and collapsible right inspector.
- Use New reconstruction, Examples, and About as the initial navigation items.
- Show Scene, Layers, and Analysis sections in the right inspector.
- Show diagnostics for arbitrary uploads, including height range, dimensions, resolution, model identity, and geospatial metadata when available.
- Show RMSE, MAE, Pearson correlation, ground truth, prediction, and error-map views only for reference-backed benchmark examples or future reference-raster comparisons.
- Include a built-in GAMUS benchmark section with precomputed validation examples.
- Do not include downloads, authentication, cloud storage, production deployment, project history, or background job orchestration in the first version.

## Testing Decisions

- Tests should verify observable behavior at the prediction API and UI seams rather than private implementation details.
- The primary integration seam is the prediction API response consumed by the frontend.
- Frontend tests should verify upload state transitions, supported-format behavior, processing/loading states, error states, result rendering, layer toggles, inspector controls, and benchmark metric display.
- Frontend scene tests should verify that a valid prediction result produces a mounted scene, that camera reset works, and that height exaggeration changes the rendered scene scale without changing the source height data.
- Backend tests should verify health behavior, accepted file types, rejection of unsupported raster formats, prediction response shape, metadata preservation, and fixture-backed synchronous responses.
- Backend tests should verify that arbitrary predictions omit accuracy metrics and benchmark results include the expected metrics and reference assets.
- GeoTIFF tests should use small fixture rasters with known CRS, bounds, transform, resolution, and RGB band structure.
- Prediction-service tests should verify the contract independently of whether the implementation is a fixture or the DepthAnything V2 checkpoint.
- Metric tests should verify RMSE, MAE, and Pearson correlation against small known arrays, including flat or degenerate cases where correlation needs safe handling.
- Visual regression tests are optional for the first version but should be considered for the application shell and primary empty/result states once the layout stabilizes.
- There is no existing application test suite or prior art in the repository; tests should establish the initial behavioral conventions.

## Out of Scope

- SRTM fetching and absolute DSM generation.
- Full-resolution tiled inference.
- Multispectral or non-RGB imagery.
- Automatic road, water, and vegetation segmentation.
- Exact architectural reconstruction or photorealistic building roofs.
- First-person flight controls as the primary interaction.
- Downloading predictions or exporting GeoTIFF/numeric output from the UI.
- User accounts, authentication, project history, collaboration, and cloud storage.
- Background job queues and distributed inference.
- Production hosting and deployment automation.
- Electron or desktop packaging.
- Unity, Cesium, or globe-scale visualization.
- Claiming arbitrary-upload accuracy without reference data.

## Further Notes

- The current fine-tuned model captures broad height structure but has soft boundaries and limited fine geometry. The renderer should improve presentation without hiding that uncertainty.
- Validation results currently suggest learned structure but should be presented as benchmark evidence rather than precision surveying. The notebook reported approximately 8–10 m validation RMSE, 5–6 m MAE, and 0.3–0.4 Pearson correlation in the observed run.
- GAMUS is primarily urban US data. The About section should explain that performance outside the training domain may be weaker.
- Dense forest scenes represent canopy height more reliably than bare-ground elevation from a single RGB image.
- The frontend should remain independent of whether the backend result is generated by a fixture, local GPU inference, or a future inference service.
