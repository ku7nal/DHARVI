# 06 — Integrate the Production Checkpoint and Full-Image Inference

**What to build:** The exact trained checkpoint loads through the application's production inference path and produces complete predictions for arbitrary image sizes. Training, evaluation, and website inference agree on normalization, tiled blending, test-time augmentation, output units, semantic IDs, invalid-pixel handling, and checkpoint metadata.

**Blocked by:** 05 — Add Semantic and Building-Boundary Supervision.

**Status:** ready-for-agent

- [ ] The production service loads the selected checkpoint without ad hoc architecture substitution or incompatible taxonomy remapping.
- [ ] A real uploaded PNG/JPEG and a representative large image reach the prediction API and return finite height and semantic outputs.
- [ ] Overlapping tiled inference, weighted blending, and flip test-time augmentation cover the complete input footprint without edge gaps or seams.
- [ ] The API reports the correct model identity, seven-class taxonomy, height units, output dimensions, and prediction provenance.
- [ ] The checkpoint passes a production-load and inference verification run before being used by the website.
