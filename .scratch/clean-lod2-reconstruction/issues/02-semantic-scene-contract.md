# 02 — Add a semantic scene contract

**What to build:** The reconstruction result can carry and display the six GAMUS semantic classes—ground, low vegetation, building, water, road, and tree—using a fixture-backed semantic result so the full API-to-viewer path is testable before model training is available.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Prediction responses expose semantic class metadata and a spatially aligned class grid.
- [ ] The frontend can inspect semantic classes without breaking height-only or legacy predictions.
- [ ] A deterministic fixture includes all six classes and verifies class/image/height alignment.
- [ ] The UI clearly distinguishes fixture or fallback semantics from trained semantic predictions.
