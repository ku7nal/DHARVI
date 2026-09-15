# 04 — Build continuous semantic terrain surfaces

**What to build:** Semantic classes render on a shared continuous terrain surface so adjacent cells do not separate vertically or appear as floating pixels from oblique camera angles. Palette colors, existing layer toggles, grounded building placement, and flat tree rendering remain intact.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Every enabled semantic class is rendered on continuous terrain geometry without visible cracks or disconnected cell edges.
- [ ] Semantic palette colors, class coverage, and existing Ground, Roads, Water, Vegetation, Trees, and Buildings controls remain correct.
- [ ] Building extrusions remain aligned to their semantic ground reference and tree predictions remain flat semantic surfaces.
- [ ] The shared surface renders correctly from isometric, top, and fly camera views.
