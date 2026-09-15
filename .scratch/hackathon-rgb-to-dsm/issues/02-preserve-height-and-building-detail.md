# 02 — Preserve high-resolution heights and building detail

**What to build:** Uploaded scenes retain continuous height detail and small building geometry instead of having semantic regions flatten or erase the reconstruction.

**Blocked by:** 01 — Correct GAMUS taxonomy and retrain the final multitask checkpoint.

**Status:** ready-for-agent

- [ ] Preserve predicted heights for ground and vegetation while using building masks only to estimate local ground and building geometry.
- [ ] Extract building regions from full-resolution predictions before reducing the terrain grid.
- [ ] Preserve polygon holes, roof-height variation, and small valid buildings.
- [ ] Keep the existing API shape compatible while returning detailed `buildingRegions` and a reduced semantic preview.
- [ ] Add regression coverage for building extraction and height preservation.
