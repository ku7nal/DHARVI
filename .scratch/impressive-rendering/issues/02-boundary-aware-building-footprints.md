# 02 — Boundary-aware building footprints

**What to build:** Extract buildings from cleaned boundaries rather than coarse bounding boxes so footprints follow roofs and adjacent structures remain separated.

**Blocked by:** 01 — Artifact-free semantic terrain rendering

**Status:** ready-for-human

- [x] Building contours are cleaned, simplified, and polygonized.
- [x] Small false-positive regions are removed and adjacent buildings are not merged unnecessarily.
- [x] Extrusions use local ground height and robust per-building height estimates.
- [x] Large buildings in `zaalima.jpeg` no longer appear as oversized rectangular slabs.
