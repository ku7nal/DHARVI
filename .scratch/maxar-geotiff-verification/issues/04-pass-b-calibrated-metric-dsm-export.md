# 04 — Pass B: calibrated metric DSM export on real GeoTIFFs

**What to build:** Each Maxar tile, uploaded with a plausible ground elevation value, produces a calibrated metric DSM that can be downloaded as a standards-compliant GeoTIFF preserving the source spatial reference.

**Blocked by:** 03 — Pass A: real GeoTIFFs through the relative nDSM path.

**Status:** resolved

- [x] Each tile, uploaded with a plausible site ground elevation (roughly 10 m Florida, 15 m San Juan coastal, 550 m Kahramanmaras), returns a `calibrated` status.
- [x] Each calibrated response reports calibration method, confidence, residual error, and ground pixel count.
- [x] Each response provides a downloadable DSM GeoTIFF.
- [x] Each downloaded DSM validates: float32, single band, CRS and bounds matching the source tile.
- [x] DSM height values are sane for the scene type — buildings tens of meters above ground, not thousands or negatives everywhere.
- [x] If calibration legitimately fails (e.g. too few ground pixels from the semantic head), the explicit non-metric status is recorded as a finding, not treated as a test error.

## Comments

**Resolved — all three fixtures calibrate and export valid metric DSM GeoTIFFs. No failures, no legitimate-failure cases triggered.**

Environment: same running `--reload` server, `dinosaur.pth` checkpoint. Uploads via `curl -F "file=@<window>.tif" -F "ground_elevation=<value>"`.

### Calibration results

| Fixture | Ground elev supplied | Time | Status | Method | Confidence | Residual error | Ground pixels |
|---|---|---|---|---|---|---|---|
| `fort-myers-fl-window.tif` | 10 m | 28.6s | `calibrated` | `ground_pixels_plus_ground_elevation` | 0.9982 | 0.018 | 1,265,259 |
| `san-juan-pr-window.tif` | 15 m | 74.4s | `calibrated` | `ground_pixels_plus_ground_elevation` | 0.9961 | 0.059 | 696,692 |
| `kahramanmaras-tr-window.tif` | 550 m | 72.1s | `calibrated` | `ground_pixels_plus_ground_elevation` | 0.9999 | 0.030 | 292,525 |

All responses report `heightReference: "absolute"` with a `dsmUrl`. The Pass A observation about 4× ground-pixel spread did not prevent any calibration — even the lowest evidence count (292k ground pixels of 4.2M total) cleared the ≥1% minimum comfortably.

### DSM GeoTIFF validation (downloaded and opened with rasterio)

All three DSMs pass every check:

- float32, single band, GTiff driver
- CRS, affine transform, bounds, and dimensions **exactly match** the source window rasters
- Values physically sane — ground pinned at the supplied elevation, buildings rising 10–22 m above it:

| Fixture | DSM p1 | p50 | p99 | max | Interpretation |
|---|---|---|---|---|---|
| Fort Myers | 10.0 | 10.0 | 13.0 | 22.0 | ground at 10 m, structures to 12 m AGL |
| San Juan | 15.0 | 15.0 | 25.0 | 31.1 | ground at 15 m, structures to 16 m AGL |
| Kahramanmaras | 550.0 | 550.0 | 558.1 | 561.7 | ground at 550 m, structures to 12 m AGL |

### Findings

None blocking. Two observations for ticket 05:

1. The Pass A→B upload time roughly doubled for identical files (38s→74s San Juan, 48s→72s Kahramanmaras) — calibration itself is cheap, so the variance is likely model-load warm/cold paths or CPU load; not investigated further.
2. Confidence values (0.996–0.9999) are uniformly high because the residual-error term is measured against the model's own ground-pixel consistency, not against independent truth. The confidence number should not be read as real-world accuracy of the 10 m / 15 m / 550 m anchors — those were plausible guesses, and the DSM inherits whatever error is in them. Worth stating explicitly in the final evidence report.
