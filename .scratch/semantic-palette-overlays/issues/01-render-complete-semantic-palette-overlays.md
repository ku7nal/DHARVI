# 01 — Render complete semantic palette overlays

**What to build:** The scene renders every aligned semantic grid cell as a flat, unlit color using the exact semantic-preview palette. Roads, low vegetation, water, trees, ground, buildings, and “others” remain visible at class boundaries instead of disappearing when neighboring cells differ.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] Every valid semantic grid cell produces a visible scene cell, including mixed-class boundaries.
- [ ] Scene colors come from the semantic class palette supplied by the prediction, with the existing palette as a legacy fallback.
- [ ] Semantic cells use flat unlit materials so rendered colors match the semantic preview independently of scene lighting.
- [ ] Roads, vegetation, water, trees, ground, buildings, and “others” are represented without changing the backend prediction response shape.
