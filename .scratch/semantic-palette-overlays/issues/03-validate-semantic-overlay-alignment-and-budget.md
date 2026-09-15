# 03 — Validate semantic overlay alignment and rendering budget

**What to build:** Regression checks verify exact palette mapping, complete mixed-class coverage, aligned grid dimensions, safe invalid-class fallback, and acceptable geometry/instance counts for a 256×256 scene.

**Blocked by:** 01 — Render complete semantic palette overlays

**Status:** ready-for-agent

- [ ] Tests verify semantic IDs map to the exact preview colors.
- [ ] Tests verify mixed-class boundaries do not create missing road or vegetation cells.
- [ ] Tests verify semantic data, semantic grid size, and scene grid remain aligned.
- [ ] Tests enforce a bounded geometry/instance budget for a 256×256 semantic grid.
- [ ] Invalid semantic IDs fall back safely without crashing or producing undefined materials.
