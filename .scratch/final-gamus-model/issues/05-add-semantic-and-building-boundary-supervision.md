# 05 — Add Semantic and Building-Boundary Supervision

**What to build:** The height model is extended or fine-tuned with the complete GAMUS seven-class semantic target and a building-boundary target. The final checkpoint predicts nDSM height, semantic classes, and building boundaries from RGB alone while keeping height quality as the primary objective.

**Blocked by:** 04 — Train the Complete GAMUS RGB-to-nDSM Model.

**Status:** ready-for-agent

- [ ] The model predicts the official taxonomy: `0=others`, `1=ground`, `2=low vegetation`, `3=building`, `4=water`, `5=road`, and `6=tree`.
- [ ] Semantic and boundary targets are aligned with RGB and height data and ignore invalid pixels.
- [ ] The multitask objective uses class-balanced semantic supervision and boundary supervision without allowing auxiliary tasks to dominate height learning.
- [ ] Validation reports height RMSE, MAE, correlation, semantic mIoU, per-class IoU, building IoU/F1, and building-boundary F1.
- [ ] The selected multitask checkpoint preserves the baseline height model identity and records whether auxiliary supervision improved or degraded height metrics.
