# 04 — Improve interactive rendering performance and navigation

**What to build:** The 3D scene remains detailed near the camera, responsive during navigation, and visually uncluttered by unnecessary tree geometry.

**Blocked by:** 02 — Preserve high-resolution heights and building detail.

**Status:** ready-for-agent

- [ ] Disable tree rendering by default.
- [ ] Use level-of-detail geometry for distant buildings and preserve detailed polygons nearby.
- [ ] Avoid one React/Three.js mesh per tree pixel; use capped instancing if trees are enabled.
- [ ] Add first-person/fly navigation while retaining orbit and top-down camera modes.
- [ ] Add height inspection and slope visualization for the rendered scene.
- [ ] Verify acceptable frame rate and memory use on the target demo machine.
