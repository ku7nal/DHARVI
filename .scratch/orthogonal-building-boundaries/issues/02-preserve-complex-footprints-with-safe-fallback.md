# 02 — Preserve complex footprints with safe fallback

**What to build:** Apply boundary cleanup conservatively so meaningful L-shaped footprints and holes remain recognizable, while diagonal or ambiguous outlines safely retain the existing simplified polygon when orthogonalization is unsafe.

**Blocked by:** 01 — Orthogonalize noisy rectangular building footprints.

**Status:** ready-for-agent

- [ ] L-shaped and other meaningful concave footprints are not replaced by bounding rectangles.
- [ ] Interior holes remain valid, aligned, and independently cleaned where safe.
- [ ] Self-intersecting, degenerate, diagonal, or ambiguous orthogonalization results are rejected in favor of the simplified polygon.
- [ ] Roof inference, ground height, wall height, and building-region metadata remain unchanged.

