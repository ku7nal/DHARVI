# 03 — Validate clean boundaries across rendering paths

**What to build:** Verify that orthogonalized building boundaries improve the rendered city without introducing geometry, placement, performance, or browser regressions.

**Blocked by:** 01 — Orthogonalize noisy rectangular building footprints; 02 — Preserve complex footprints with safe fallback.

**Status:** complete

- [x] Backend tests cover noisy rectangles, clean rectangles, L-shaped footprints, holes, diagonal outlines, fallback behavior, winding, area, extent, and self-intersection safety.
- [x] Frontend geometry and scene-quality checks continue to pass with cleaned and fallback footprints.
- [x] Browser screenshots of representative isometric, top, and fly views show straighter building walls without floating, sinking, severe overlap, or console errors.
- [x] Existing roof styles, LOD tiers, layer toggles, and browser performance safeguards remain intact.
