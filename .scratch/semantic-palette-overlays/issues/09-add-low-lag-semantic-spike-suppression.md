# 09 — Add low-lag semantic spike suppression

**What to build:** Green semantic overlays no longer show sharp height spikes from oblique camera angles, while broad terrain relief remains visible and scene interaction stays responsive.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Low-vegetation and tree surfaces use a cheap single-pass corner-height filter that suppresses isolated extremes without iterative neighborhood smoothing.
- [ ] Semantic overlay geometries are memoized and disposed when their inputs change, avoiding repeated geometry construction and GPU resource growth during UI or camera interaction.
- [ ] Building heights and ground alignment remain unchanged, while roads and water remain level at the prepared terrain baseline.
- [ ] Semantic colors, layer toggles, tree rendering behavior, backend prediction data, and model outputs remain unchanged.
- [ ] Focused regression checks cover spike suppression, preserved broad relief, stable roads/water, and building alignment.
