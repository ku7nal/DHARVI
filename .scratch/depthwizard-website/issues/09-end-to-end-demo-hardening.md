# 09 — End-to-end demo hardening

**What to build:** The local demo is reliable across supported inputs, communicates limitations clearly, handles failures, and meets the intended presentation quality.

**Blocked by:** 06 — Benchmark and accuracy workspace; 07 — Stylized city geometry; 08 — DepthAnything V2 model integration

**Status:** ready-for-agent

- [ ] The complete flow works from upload or example selection through real prediction and 3D exploration.
- [ ] Supported PNG, JPEG, RGB GeoTIFF, and RGBA GeoTIFF flows are verified.
- [ ] Unsupported input errors are clear and recoverable.
- [ ] The benchmark flow remains distinct from arbitrary-upload diagnostics.
- [ ] The interface consistently communicates estimated nDSM semantics, meter units, model identity, and domain limitations.
- [ ] The scene, inspector, benchmark views, and navigation remain usable at the demo viewport size.
- [ ] Camera controls, layer toggles, reset behavior, and height exaggeration work together without mutating source prediction data.
- [ ] The local development and demo startup instructions are complete.
