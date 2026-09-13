# 02 — Reference-style reconstruction workflow

**What to build:** Apply the new reference-inspired visual system across the complete reconstruction journey without changing prediction behavior: upload, processing, errors, successful results, interactive 3D scene, inspector, layer controls, metadata, and reset actions.

**Blocked by:** 01 — Reference-style application shell and navbar

**Status:** resolved

- [x] PNG, JPEG, RGB GeoTIFF, RGBA GeoTIFF, drag-and-drop, and built-in GAMUS example flows continue to work.
- [x] Processing and failure states use the new typography, spacing, cards, buttons, and violet accent system with clear recovery actions.
- [x] Successful predictions retain the interactive 3D viewer, camera controls, height exaggeration, layer toggles, previews, analysis metadata, and downloads.
- [x] The result viewer and inspector feel visually cohesive with the reference-style shell while remaining readable and functional.
- [x] The user can start a new reconstruction from the navbar CTA and result state without losing existing behavior.
- [x] Estimated nDSM semantics, meter units, model identity, and geospatial limitations remain clearly communicated.

## Implementation notes

The workflow reuses the existing prediction contract and interaction components. Changes are limited to reference-style presentation, state affordances, responsive viewer/inspector layout, and visual hierarchy.
