# 10 — Validate low-lag semantic overlays

**What to build:** The semantic scene has regression coverage proving that spike suppression and geometry caching preserve visual continuity, correctness, and the existing rendering budget.

**Blocked by:** 09 — Add low-lag semantic spike suppression

**Status:** ready-for-agent

- [ ] Semantic geometry positions and normals remain finite and upward-facing across representative overlays.
- [ ] Shared class boundaries remain continuous and local height differences stay within the defined smoothing threshold.
- [ ] Roads and water remain stable, building ground alignment is preserved, and broad relief remains visible after cleanup.
- [ ] Palette values, layer toggles, camera stability, and the 256 × 256 geometry budget remain covered by regression checks.
- [ ] Frontend typecheck, terrain, scene, building, quality, and production-build checks pass without backend or model-output changes.
