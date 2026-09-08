# 04 — Prediction analysis inspector

**What to build:** The right inspector explains the prediction and controls the scene, showing estimated nDSM metadata, model identity, dimensions, resolution, layer toggles, raw height-map preview, RGB preview, and wireframe mode.

**Blocked by:** 02 — Fixture-backed reconstruction upload

**Status:** ready-for-agent

- [ ] The inspector contains collapsible Scene, Layers, and Analysis sections.
- [ ] The Analysis section labels the result as Estimated nDSM in meters or Estimated height above ground.
- [ ] The Analysis section shows model identity and GAMUS fine-tuning context.
- [ ] The Analysis section shows image dimensions, prediction dimensions, and estimated nDSM range.
- [ ] The Layers section toggles stylized city, estimated nDSM surface, RGB texture, and wireframe views.
- [ ] The RGB preview and height-map preview are available without leaving the result workspace.
- [ ] The inspector does not display accuracy metrics for an arbitrary fixture upload without reference data.
