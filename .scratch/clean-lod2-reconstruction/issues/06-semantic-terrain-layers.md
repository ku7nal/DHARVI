# 06 — Build semantic terrain and non-building layers

**What to build:** Ground, roads, water, vegetation, and trees render as stable semantic scene layers around procedural buildings, with smoothed terrain and no large nDSM spikes contaminating the city view.

**Blocked by:** 03 — Train and evaluate the GAMUS multitask model; 04 — Generate regularized building footprints

**Status:** ready-for-agent

- [ ] Terrain is edge-preservingly smoothed outside building footprints.
- [ ] Roads and water remain visually stable and do not become tall terrain artifacts.
- [ ] Vegetation and trees use bounded low-poly or billboard geometry rather than raw height spikes.
- [ ] Scene layer controls expose ground, roads, water, vegetation, trees, buildings, and optional relief.
- [ ] A semantic fixture verifies that non-building classes remain outside building geometry.
