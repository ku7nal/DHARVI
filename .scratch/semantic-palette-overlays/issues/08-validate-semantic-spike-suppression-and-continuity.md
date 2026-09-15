# 08 — Validate semantic spike suppression and continuity

**What to build:** Regression checks verify that moderated semantic height smoothing produces stable, continuous overlays without sharp spikes while preserving roads, water, buildings, palettes, layer behavior, and the existing 256×256 rendering budget.

**Blocked by:** 07 — Smooth shared semantic terrain heights

**Status:** ready-for-agent

- [ ] Tests verify semantic geometry positions and normals remain finite and upward-facing.
- [ ] Tests verify shared class boundaries have identical edge heights after smoothing.
- [ ] Tests enforce a bounded local height difference for semantic vertices.
- [ ] Tests verify roads and water remain stable and building ground alignment is preserved.
- [ ] Tests retain palette, layer-toggle, camera-stability, and 256×256 geometry-budget coverage.
