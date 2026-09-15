# 01 — Stabilize the procedural city render

**What to build:** The viewer presents a clean, grounded procedural city as its default result, with correctly aligned walls and roofs, neutral CAD-style materials, sharper lighting, and optional nDSM/RGB relief inspection layers.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Building walls sit on the terrain and roofs connect to wall tops without floating or sinking.
- [ ] The default city view uses clean procedural materials, controlled shading, directional shadows, and contact separation.
- [ ] Estimated nDSM and RGB relief are optional inspection layers and do not obscure the procedural city by default.
- [ ] A fixture-backed viewer check covers wall/roof alignment and the default layer state.
