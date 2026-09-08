# 08 — DepthAnything V2 model integration

**What to build:** The real fine-tuned DepthAnything V2 Small checkpoint replaces fixture predictions behind the existing prediction service, reproduces the notebook preprocessing, and renders real estimated nDSM results through the website.

**Blocked by:** 03 — Interactive 3D reconstruction viewer; 04 — Prediction analysis inspector; 05 — GeoTIFF-aware input handling

**Status:** resolved

- [x] The backend loads the fine-tuned DepthAnything V2 Small state dict using the same model wrapper used during training.
- [x] Inference accepts RGB input and applies the notebook’s ImageNet normalization and 518×518 input preparation.
- [x] Inference returns non-negative estimated nDSM values in meters.
- [x] The prediction service preserves the public response contract used by fixture results.
- [x] A real PNG or JPEG upload renders a real predicted nDSM in the existing viewer.
- [x] A real RGB or RGBA GeoTIFF upload renders a real predicted nDSM while preserving geospatial metadata.
- [x] The UI labels the result as Estimated nDSM in meters and does not claim absolute DSM.
- [x] Model-loading and inference failures produce clear user-facing errors.

## Answer

Implemented the fine-tuned `astra.pth` checkpoint behind the existing prediction API. Uploaded PNG/JPEG and RGB/RGBA GeoTIFF inputs now run the DepthAnything V2 Small wrapper from `mynotebook.ipynb`, apply ImageNet normalization with 518×518 center-crop preparation, return nonnegative estimated nDSM values, preserve GeoTIFF metadata, and render through the existing viewer. The GAMUS example remains fixture-backed for fast UI checks.

Validation included the backend test suite, frontend typecheck/build, direct checkpoint inference, a real PNG API upload, and a real RGB GeoTIFF API upload. Missing dependencies/checkpoints and inference failures return clear API errors.
