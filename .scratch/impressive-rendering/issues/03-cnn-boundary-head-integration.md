# 03 — CNN boundary-head integration

**What to build:** Use the existing CNN boundary prediction during inference to sharpen building separation and improve footprint extraction without introducing a generative model that can invent geometry.

**Blocked by:** 02 — Boundary-aware building footprints

**Status:** ready-for-human

- [x] Boundary predictions are consumed by the reconstruction pipeline and remain spatially aligned.
- [x] Boundary-aware extraction improves building-boundary validation metrics or an equivalent measured baseline.
- [x] Low-confidence boundaries have a safe fallback or visible uncertainty state.
- [x] The pipeline does not hallucinate buildings, roads, or roof geometry during postprocessing.
