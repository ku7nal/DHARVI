# 02 — Footprint-aware building replacement

**What to build:** Use the low-poly archetypes throughout the reconstructed scene, fitting them to detected building footprints and preserving existing placement, ground height, height exaggeration, roof metadata, visibility controls, and procedural fallback behavior.

**Blocked by:** 01 — Low-poly building archetype generator.

**Status:** ready-for-agent

- [ ] Buildings are placed from existing building regions and remain aligned with their detected footprints and ground heights.
- [ ] Roof selection uses available building metadata where possible and falls back safely for unsupported or malformed regions.
- [ ] Scenes with missing semantic data or unusual footprints still render without errors using a valid fallback.

