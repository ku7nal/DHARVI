# 01 — Orthogonalize noisy rectangular building footprints

**What to build:** Clean raster-derived building footprints so rectangular or near-rectangular buildings render with straight horizontal and vertical boundaries instead of pixel stair-steps, while preserving the existing `buildingRegions` contract.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] Noisy rectangular masks produce substantially fewer footprint vertices and predominantly straight axis-aligned edges.
- [ ] Clean rectangular footprints retain their approximate extent, winding, non-zero area, and building placement.
- [ ] Normalized footprint output remains compatible with existing wall, roof, height, and LOD rendering.

