# 04 — Train the Complete GAMUS RGB-to-nDSM Model

**What to build:** The selected model is trained on the complete official GAMUS training split using native-resolution random crops rather than resizing full tiles down to model resolution. The run uses masked meter-scale height supervision, target-dependent emphasis for buildings and tall structures, gradient preservation, mixed precision, warmup, gradient clipping, resumable checkpoints, and full-image validation.

**Blocked by:** 03 — Select the Final Model and Training Protocol.

**Status:** ready-for-agent

- [ ] All available official training samples are used without silently dropping valid tiles or modalities.
- [ ] Training crops preserve original spatial detail and apply identical geometric transforms to RGB and height targets.
- [ ] Invalid height pixels are masked, and the loss is not self-normalized by the model's current error.
- [ ] The height objective remains primary while bounded target-dependent weighting improves learning on buildings and tall structures.
- [ ] Warmup, cosine or otherwise documented learning-rate scheduling, mixed precision, gradient accumulation, gradient clipping, and resumable checkpoints work on Kaggle.
- [ ] The best height checkpoint is selected from complete-image validation and includes configuration and metric metadata.
