# 03 — Select the Final Model and Training Protocol

**What to build:** A controlled Kaggle pilot compares viable Depth Anything V2 model sizes and training configurations using the verified data path. The project selects one configuration based on height accuracy, building-boundary quality, visual output, inference cost, and checkpoint size, then freezes the protocol for final training.

**Blocked by:** 02 — Kaggle Training Pipeline Smoke Test.

**Status:** ready-for-agent

- [ ] Depth Anything V2 Small and Base are compared when both fit the available Kaggle accelerator, or the accelerator-appropriate model is justified when only one fits.
- [ ] All candidates use identical data auditing, native-resolution crop sampling, target handling, validation, and reporting conventions.
- [ ] The selected input size, crop sampler, augmentation policy, loss weights, optimizer, learning-rate schedule, batch strategy, and checkpoint contract are recorded.
- [ ] The selection report includes height RMSE/MAE/correlation, building-boundary quality, qualitative montages, inference time, memory behavior, and checkpoint size.
