# 02 — Kaggle Training Pipeline Smoke Test

**What to build:** A small, fast Kaggle run proves that the complete training path works before the full dataset is used. The run exercises data loading, native-resolution crops, augmentation, forward and backward passes, mixed precision, gradient accumulation, validation, full-image tiled inference, visualization, checkpointing, resuming, and production checkpoint loading.

**Blocked by:** 01 — Complete GAMUS Dataset Ingestion and Audit.

**Status:** ready-for-agent

- [ ] A smoke run on approximately 100–300 tiles completes one or two training epochs without data, shape, device, or memory errors.
- [ ] The run uses the same native-resolution crop, target handling, model wrapper, and loss path intended for the full run.
- [ ] Full 1024×1024 tiled inference with overlap and horizontal-flip test-time augmentation completes on representative validation tiles.
- [ ] RGB, target nDSM, predicted nDSM, absolute-error, semantic, and building-boundary visualizations are produced.
- [ ] Predictions are finite, non-negative, non-constant, and use semantic IDs `0..6`; the model does not collapse to all-ground output.
- [ ] A saved checkpoint can be resumed and loaded by the same wrapper used by the application.
