# 05 — Smooth semantic regions while preserving road boundaries

**What to build:** Ground and vegetation semantic regions appear filled and visually smooth instead of pixelated, while roads remain continuous corridors with sharp, well-defined categorical boundaries. Small non-road speckles and holes are cleaned up without changing backend prediction data.

**Blocked by:** 04 — Build continuous semantic terrain surfaces

**Status:** ready-for-agent

- [ ] Ground and vegetation regions have simplified, filled boundaries that look stable from every camera direction.
- [ ] Roads retain their predicted coverage and use sharp boundaries without being blurred, disconnected, or removed by cleanup.
- [ ] Water, buildings, trees, and “others” remain represented with their exact semantic palette colors.
- [ ] Existing layer toggles independently show and hide the smoothed class geometry.
