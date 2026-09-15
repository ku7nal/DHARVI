# 07 — Validate Official and Out-of-Domain Landscape Performance

**What to build:** The project produces defensible quantitative and visual evidence for the official GAMUS test split and clearly separated evidence for urban, sparse, hilly, and forested conditions. GAMUS-backed results, external results, and synthetic stress fixtures are labeled according to their actual evidence status.

**Blocked by:** 06 — Integrate the Production Checkpoint and Full-Image Inference.

**Status:** ready-for-agent

- [ ] Official GAMUS test evaluation uses full-image tiled inference and reports RMSE, MAE, Pearson correlation, semantic mIoU, per-class IoU, building IoU/F1, and building-boundary F1.
- [ ] Results are broken down by city, height range, ground versus non-ground pixels, buildings, and tall structures.
- [ ] The report includes aligned RGB, reference nDSM, prediction, absolute-error, semantic, and boundary visual comparisons.
- [ ] Urban, sparse, hilly, and forested results are separated by dataset source and evidence status; synthetic fixtures are never presented as measured validation.
- [ ] Known limitations involving GAMUS's urban coverage, canopy height, terrain relief, occlusion, shadows, and relative-versus-absolute height are documented.
