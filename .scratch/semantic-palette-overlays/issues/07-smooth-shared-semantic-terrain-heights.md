# 07 — Smooth shared semantic terrain heights

**What to build:** Semantic overlays retain broad terrain relief without producing sharp dark-green spikes or triangular wedges from oblique camera angles. Roads and water remain stable, buildings retain their existing ground alignment and heights, and model/backend outputs remain unchanged.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Shared semantic vertices use moderated neighboring terrain heights that remove extreme local spikes while preserving broad relief.
- [ ] Roads and water retain stable surfaces and are not vertically distorted by smoothing.
- [ ] Building cells and building extrusions remain aligned to their existing region ground heights.
- [ ] Semantic colors, layer toggles, tree rendering, and backend prediction data remain unchanged.
