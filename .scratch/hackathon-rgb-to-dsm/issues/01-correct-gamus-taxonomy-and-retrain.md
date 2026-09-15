# 01 — Correct GAMUS taxonomy and retrain the final multitask checkpoint

**What to build:** A validated seven-class GAMUS height/semantic/boundary model that uses the official label mapping and can be loaded by the live prediction pipeline.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] Train with `0=others`, `1=ground`, `2=low vegetation`, `3=building`, `4=water`, `5=road`, and `6=tree`.
- [ ] Produce a checkpoint with seven semantic channels and building class `3`.
- [ ] Report validation/test height RMSE, MAE, correlation, per-class IoU, building IoU, and building-boundary F1.
- [ ] Verify the checkpoint loads through the backend model service and produces class IDs in `0..6`.
