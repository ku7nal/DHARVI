# 02 — Clean semantic masks and building footprints

**What to build:** Semantic predictions are resized from logits before classification, denoised, filtered for tiny regions, and converted into stable building footprints with clean walls and controlled holes. The resulting geometry matches visible building boundaries more closely.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] Semantic logits are resized to the scene grid before `argmax`, preserving the best available boundary information.
- [ ] Deterministic postprocessing removes isolated label noise, tiny components, and insignificant building holes without adding a new runtime dependency.
- [ ] Building regions are generated from the cleaned aligned mask with controlled contour simplification, valid winding, nonnegative wall heights, and stable holes.
- [ ] Backend tests cover semantic alignment, cleanup behavior, and footprint extraction; existing health and building-footprint tests continue to pass.
