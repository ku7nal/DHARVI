# 07 — Stylized city geometry

**What to build:** The height surface becomes a cleaner stylized city with height-threshold building extraction, mask cleanup, filtered building footprints, extruded structures, neutral non-building terrain, and reference-inspired materials and lighting.

**Blocked by:** 03 — Interactive 3D reconstruction viewer

**Status:** ready-for-agent

- [ ] The renderer derives an initial building mask from estimated nDSM height values.
- [ ] Small noisy components are removed through configurable cleanup and minimum-area filtering.
- [ ] Building regions become clean local footprints suitable for extrusion.
- [ ] Building footprints are extruded using estimated metric height.
- [ ] Non-building surfaces use a neutral terrain material rather than unsupported semantic labels.
- [ ] The stylized city is the default layer after prediction.
- [ ] Materials use the restrained reference-inspired palette.
- [ ] Lighting and shadows make building volumes legible from the isometric camera.
- [ ] The raw estimated nDSM surface remains available as an alternate layer.
