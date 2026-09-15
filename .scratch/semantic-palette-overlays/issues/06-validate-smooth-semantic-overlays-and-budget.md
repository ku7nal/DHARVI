# 06 — Validate smooth semantic overlays and rendering budget

**What to build:** Regression checks verify that smoothed semantic overlays preserve class coverage, road continuity, building alignment, camera-angle stability, exact palette colors, and acceptable rendering cost for a 256×256 scene.

**Blocked by:** 05 — Smooth semantic regions while preserving road boundaries

**Status:** ready-for-agent

- [ ] Tests verify complete semantic coverage with no gaps at mixed-class boundaries.
- [ ] Tests verify roads remain continuous and sharply bounded after smoothing and cleanup.
- [ ] Tests verify building ground alignment and upward-facing/shared terrain geometry.
- [ ] Tests verify exact palette mapping, safe invalid-class fallback, and independent layer behavior.
- [ ] Tests enforce bounded geometry counts for a 256×256 semantic grid and stable rendering from supported camera modes.
