# 02 — Connect semantic colors to scene layer controls

**What to build:** Existing Ground, Roads, Water, Vegetation, Trees, and Buildings toggles independently control their corresponding semantic colors and geometry. Tree cones are removed from the semantic path so tree predictions render as the same flat palette color as the preview.

**Blocked by:** 01 — Render complete semantic palette overlays

**Status:** ready-for-agent

- [ ] Ground, roads, water, low vegetation, trees, and buildings respond to their existing layer toggles.
- [ ] Tree predictions render as flat semantic colors when enabled and disappear when the Trees layer is disabled.
- [ ] Building visibility remains compatible with clean flat building extrusions from the earlier reconstruction tickets.
- [ ] Toggling one semantic class does not hide or recolor unrelated classes.
