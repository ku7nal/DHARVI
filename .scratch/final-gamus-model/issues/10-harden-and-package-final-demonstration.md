# 10 — Harden and Package the Final Demonstration

**What to build:** The complete project can be started and verified through one repeatable workflow on the demo machine. The final demonstration covers the trained model, semantic/building reconstruction, interactive navigation, validation evidence, GeoTIFF calibration, failure states, and checkpoint compatibility while clearly distinguishing measured results from fixtures and estimates.

**Blocked by:** 07 — Validate Official and Out-of-Domain Landscape Performance; 08 — Preserve Full-Resolution Building Geometry in the Scene; 09 — Deliver Calibrated GeoTIFF DSM Output.

**Status:** ready-for-agent

- [ ] One documented startup path runs the backend, frontend, and intended production checkpoint.
- [ ] One repeatable verification command covers checkpoint loading, upload failures, large-image behavior, semantic/building rendering, validation assets, calibration, and frontend checks.
- [ ] The demo shows model provenance, height and slope inspection, scene navigation, semantic/building overlays, and bounded tree rendering.
- [ ] Documentation separates official test metrics, external evaluation, synthetic stress fixtures, relative nDSM, and calibrated metric DSM claims.
- [ ] The final artifact includes the checkpoint, training configuration, dataset revision and manifest, validation/test metrics, visual evidence, known limitations, and presentation checklist.
