# 07 — Validate visual quality and browser performance

**What to build:** A 1024×1024 reconstruction can be compared against the retained baseline and rendered as a clean CAD-like city at interactive browser performance, with measurable geometry quality and honest estimated-nDSM labeling.

**Blocked by:** 01 — Stabilize the procedural city render; 05 — Infer and render clean roof geometry; 06 — Build semantic terrain and non-building layers

**Status:** ready-for-agent

- [ ] Full-image reconstruction coverage is demonstrated for a 1024×1024 input.
- [ ] Baseline and improved results can be compared using height and building-boundary metrics.
- [ ] Visual checks confirm sharp roofs, grounded walls, continuous terrain, and no façade texture smearing.
- [ ] Distant buildings use reduced geometry while nearby buildings retain LoD2 detail.
- [ ] The browser remains responsive with the target terrain grid and merged or instanced scene geometry.
