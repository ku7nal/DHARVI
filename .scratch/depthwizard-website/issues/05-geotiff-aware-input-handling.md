# 05 — GeoTIFF-aware input handling

**What to build:** RGB and RGBA GeoTIFF uploads are accepted, unsupported multispectral or non-RGB files are rejected clearly, and CRS, bounds, transform, and resolution are preserved and displayed.

**Blocked by:** 02 — Fixture-backed reconstruction upload

**Status:** resolved

- [x] The backend recognizes GeoTIFF inputs independently of filename casing.
- [x] RGB GeoTIFFs are accepted.
- [x] RGBA GeoTIFFs are accepted and converted to the model’s RGB input representation.
- [x] Multispectral or non-RGB GeoTIFFs are rejected with a clear explanation.
- [x] GeoTIFF CRS, bounds, transform, and resolution are returned in prediction metadata.
- [x] The frontend displays available geospatial metadata in the Analysis inspector.
- [x] GeoTIFF results still render in local scene coordinates.
- [x] Small fixture rasters with known metadata are covered by backend behavior tests.
