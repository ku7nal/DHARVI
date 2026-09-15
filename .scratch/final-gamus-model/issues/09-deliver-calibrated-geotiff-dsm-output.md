# 09 — Deliver Calibrated GeoTIFF DSM Output

**What to build:** A georeferenced RGB or RGBA GeoTIFF can produce a metric DSM when valid ground-elevation evidence is supplied through a DEM, SRTM/DTM source, or sufficient ground-control points. Ordinary PNG/JPEG uploads remain explicitly relative estimated nDSM products.

**Blocked by:** 06 — Integrate the Production Checkpoint and Full-Image Inference.

**Status:** ready-for-agent

- [ ] GeoTIFF inputs preserve CRS, bounds, affine transform, resolution, dimensions, band structure, and valid-pixel metadata.
- [ ] Calibration combines predicted nDSM with documented ground-elevation evidence and reports method, confidence, residual error, and evidence coverage.
- [ ] Missing CRS, insufficient ground evidence, invalid control points, and invalid spatial metadata produce explicit non-metric statuses rather than misleading output.
- [ ] Successful calibration exports a standards-compliant float32 DSM GeoTIFF preserving the source spatial reference.
- [ ] PNG/JPEG results remain labeled as relative estimated nDSM and are never presented as absolute elevation.

## Comments

**Verdict from the Maxar real-world verification exercise (2026-09-15): partially satisfied. Evidence: `.scratch/maxar-geotiff-verification/issues/01`–`05`.**

Per-criterion assessment against three real Maxar RGB GeoTIFF windows (Fort Myers FL, San Juan PR, Kahramanmaras TR; ~0.3 m GSD, UTM CRS, `dinosaur.pth` checkpoint):

1. **Metadata preservation — verified on real data.** CRS, bounds, affine transform, resolution, dimensions, band structure, and valid-pixel fraction echoed exactly (match to 1e-9) on all three uploads.
2. **Calibration reporting — partially verified.** The ground-elevation method was verified end-to-end on all three fixtures (method, confidence, residual error, ground pixel count all reported). GCP-based calibration is implemented and unit-tested but was not exercised on real imagery. The **DEM / SRTM / DTM evidence source named in this issue's "What to build" is not implemented** — ground evidence today is a user-supplied scalar or GCPs only.
3. **Explicit non-metric statuses — partially verified.** `insufficient_ground_evidence` observed on real data (correctly returned despite 292k–1.27M ground pixels, because no elevation evidence was supplied). Missing-CRS, invalid-GCP, and invalid-spatial-metadata statuses are covered by unit tests only, not observed on real uploads.
4. **Float32 DSM export — verified on real data.** All three downloaded DSMs: float32, single band, GTiff driver, CRS/transform/bounds/dimensions exactly matching source; ground pinned at supplied elevation with structures 10–16 m AGL.
5. **PNG/JPEG stay relative — unit-test backed.** Not re-verified on real imagery during this exercise (GeoTIFF-only passes).

**Recommendation:** keep this issue open. The user-supplied-evidence path is demonstrably working on real data; what remains is the DEM/SRTM ground-evidence source (or explicitly descoping it) and real-data exercise of the GCP path. Related honesty concern about confidence semantics filed separately as `.scratch/maxar-geotiff-verification/issues/06`.
