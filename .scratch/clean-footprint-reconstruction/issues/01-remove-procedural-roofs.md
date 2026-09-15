# 01 — Remove procedural roofs from building rendering

**What to build:** Uploaded reconstructions render clean, flat-topped building extrusions without roof overlap, triangulation artifacts, or roof-induced glitches. Existing roof metadata remains API-compatible but no longer affects the default scene.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] The default building scene renders one stable flat-topped extrusion per region and adds no procedural roof mesh.
- [ ] Existing prediction payloads containing roof metadata continue to load without breaking the viewer.
- [ ] Geometry and scene-quality checks verify valid walls, normals, grounded heights, and browser vertex budget.
- [ ] Frontend typecheck, build, and scene tests pass.
