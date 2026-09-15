# 04 — Generate regularized building footprints

**What to build:** Semantic building masks become clean polygon footprints that preserve small structures, remove isolated noise, simplify jagged boundaries, retain meaningful courtyards, and produce grounded wall extrusions in the viewer.

**Blocked by:** 02 — Add a semantic scene contract; 03 — Train and evaluate the GAMUS multitask model

**Status:** ready-for-agent

- [ ] Connected components preserve legitimate small buildings while removing only isolated noise.
- [ ] Building masks are polygonized and simplified without collapsing meaningful irregular outlines.
- [ ] Predicted eave/ground heights are estimated from surrounding terrain pixels.
- [ ] API and viewer use the polygon footprint for wall geometry instead of rectangular bounding blobs.
- [ ] Tests cover adjacent buildings, holes, small buildings, and noisy mask pixels.
