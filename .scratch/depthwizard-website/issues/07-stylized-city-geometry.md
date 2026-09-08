# 07 — Stylized city geometry

**What to build:** The height surface becomes a cleaner stylized city with height-threshold building extraction, mask cleanup, filtered building footprints, extruded structures, neutral non-building terrain, and reference-inspired materials and lighting.

**Blocked by:** 03 — Interactive 3D reconstruction viewer

**Status:** resolved

- [x] The renderer derives an initial building mask from estimated nDSM height values.
- [x] Small noisy components are removed through configurable cleanup and minimum-area filtering.
- [x] Building regions become clean local footprints suitable for extrusion.
- [x] Building footprints are extruded using estimated metric height.
- [x] Non-building surfaces use a neutral terrain material rather than unsupported semantic labels.
- [x] The stylized city is the default layer after prediction.
- [x] Materials use the restrained reference-inspired palette.
- [x] Lighting and shadows make building volumes legible from the isometric camera.
- [x] The raw estimated nDSM surface remains available as an alternate layer.
