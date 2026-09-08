# 05 — GeoTIFF-aware input handling

**What to build:** RGB and RGBA GeoTIFF uploads are accepted, unsupported multispectral or non-RGB files are rejected clearly, and CRS, bounds, transform, and resolution are preserved and displayed.

**Blocked by:** 02 — Fixture-backed reconstruction upload

**Status:** ready-for-agent

- [ ] The backend recognizes GeoTIFF inputs independently of filename casing.
- [ ] RGB GeoTIFFs are accepted.
- [ ] RGBA GeoTIFFs are accepted and converted to the model’s RGB input representation.
- [ ] Multispectral or non-RGB GeoTIFFs are rejected with a clear explanation.
- [ ] GeoTIFF CRS, bounds, transform, and resolution are returned in prediction metadata.
- [ ] The frontend displays available geospatial metadata in the Analysis inspector.
- [ ] GeoTIFF results still render in local scene coordinates.
- [ ] Small fixture rasters with known metadata are covered by backend behavior tests.
