# 03 — Redesign the prediction canvas and analysis inspector

**What to build:** Make the successful prediction state a map-first analysis workspace. The existing Three.js reconstruction becomes the dominant canvas, its camera and inspection controls become compact overlays, and prediction details move into dark editor-style sections for preview, semantics, layers, analysis, and GeoTIFF metadata.

**Blocked by:** 01 — Build the map-editor workspace shell

**Status:** ready-for-agent

- [ ] A successful prediction renders as a dominant canvas with compact controls for camera mode, reset, exaggeration, and terrain inspection.
- [ ] Preview, semantics, layers, and analysis sections retain their current data and interactions.
- [ ] Every existing layer toggle remains functional, including city, buildings, ground, roads, water, vegetation, trees, height, slope, RGB, and wireframe.
- [ ] Technical values use compact metadata styling and DSM download behavior remains available.
- [ ] The result workspace remains usable when semantic data or GeoTIFF metadata is unavailable.
