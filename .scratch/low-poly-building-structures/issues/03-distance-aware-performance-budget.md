# 03 — Distance-aware performance budget

**What to build:** Keep the low-poly building scene smooth by selecting appropriate detail for near, medium, and distant buildings and preserving the renderer’s existing adaptive performance safeguards.

**Blocked by:** 02 — Footprint-aware building replacement.

**Status:** ready-for-agent

- [ ] Close buildings can show the richer low-poly treatment while distant buildings use simplified geometry.
- [ ] Camera orbit, fly controls, layer toggles, and height exaggeration remain responsive in representative scenes.
- [ ] Shared geometry/materials, model counts, or equivalent safeguards keep the scene within the browser budget.
- [ ] Existing adaptive device-pixel-ratio behavior continues to reduce rendering pressure when performance declines.

