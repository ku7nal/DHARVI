# 08 — DepthAnything V2 model integration

**What to build:** The real fine-tuned DepthAnything V2 Small checkpoint replaces fixture predictions behind the existing prediction service, reproduces the notebook preprocessing, and renders real estimated nDSM results through the website.

**Blocked by:** 03 — Interactive 3D reconstruction viewer; 04 — Prediction analysis inspector; 05 — GeoTIFF-aware input handling

**Status:** ready-for-agent

- [ ] The backend loads the fine-tuned DepthAnything V2 Small state dict using the same model wrapper used during training.
- [ ] Inference accepts RGB input and applies the notebook’s ImageNet normalization and 518×518 input preparation.
- [ ] Inference returns non-negative estimated nDSM values in meters.
- [ ] The prediction service preserves the public response contract used by fixture results.
- [ ] A real PNG or JPEG upload renders a real predicted nDSM in the existing viewer.
- [ ] A real RGB or RGBA GeoTIFF upload renders a real predicted nDSM while preserving geospatial metadata.
- [ ] The UI labels the result as Estimated nDSM in meters and does not claim absolute DSM.
- [ ] Model-loading and inference failures produce clear user-facing errors.
