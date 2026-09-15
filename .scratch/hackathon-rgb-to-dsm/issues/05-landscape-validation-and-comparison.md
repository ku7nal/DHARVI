# 05 — Add landscape-stratified validation and visual comparison

**What to build:** The product provides credible quantitative and visual evidence across the landscape types in the hackathon evaluation.

**Blocked by:** 01 — Correct GAMUS taxonomy and retrain the final multitask checkpoint; 02 — Preserve high-resolution heights and building detail; 03 — Deliver metric DSM output for georeferenced imagery.

**Status:** ready-for-agent

- [ ] Report RMSE, MAE, and correlation for urban, sparse, hilly, and forested evaluation groups.
- [ ] Report semantic mIoU, building IoU, and building-boundary F1 where labels exist.
- [ ] Add input/reference/prediction/error visual comparisons.
- [ ] Distinguish validated metric DSM results from relative-only visualization results.
- [ ] Document known failure cases and dataset coverage limitations.
