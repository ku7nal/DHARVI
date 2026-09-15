# 05 — Infer and render clean roof geometry

**What to build:** Each regularized building receives a connected procedural roof—flat, gabled, hipped, or multi-plane—inferred from nDSM height structure, producing sharp CAD-like geometry without molten surfaces or RGB textures on façades.

**Blocked by:** 04 — Generate regularized building footprints

**Status:** ready-for-agent

- [ ] Roof height is estimated robustly from nDSM values inside each footprint.
- [ ] Roof type is inferred from height gradients or fitted roof planes rather than a single global threshold.
- [ ] Roof meshes share footprint edges with walls and have correct normals and winding.
- [ ] Roof materials are clean procedural materials; RGB projection is limited to roof surfaces when enabled.
- [ ] Viewer checks cover flat, gabled, hipped, and irregular footprints.
