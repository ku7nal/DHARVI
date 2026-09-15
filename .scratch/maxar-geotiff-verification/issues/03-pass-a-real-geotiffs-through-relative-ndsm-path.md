# 03 — Pass A: real GeoTIFFs through the relative nDSM path

**What to build:** Each Maxar tile, uploaded through the prediction API with no ground evidence supplied, produces a real predicted nDSM while preserving geospatial metadata and staying scientifically honest about height reference.

**Blocked by:** 02 — Fetch and validate Maxar test fixtures.

**Status:** resolved

- [x] Each of the three Maxar tiles uploads successfully via the prediction API and returns a prediction.
- [x] Each response reports `inputFormat: "geotiff"` and echoes CRS, bounds, transform, and resolution from the source tile.
- [x] Each response reports an explicit `insufficient_ground_evidence` calibration status — never a silent or misleading metric claim.
- [x] Predicted height maps render (height map URL returns an image) with plausible relative structure for urban scenes.
- [x] Any crash, hang, or wrong status is recorded in the ticket comments before Pass B begins.

## Comments

**Resolved — all three fixtures pass the relative nDSM path. No crashes, no hangs, no wrong statuses.**

Environment: the locally running `--reload` server (port 8000, current working tree, `dinosaur.pth` checkpoint — the default when `DEPTHWIZARD_CHECKPOINT` is unset).

### Results per fixture

| Fixture | Upload time | Status | Calibration status | Ground pixels | Height range (relative, m) | Height PNG nonzero |
|---|---|---|---|---|---|---|
| `fort-myers-fl-window.tif` (1536²) | 19.5s | complete | `insufficient_ground_evidence` | 1,265,259 | 0.000 – 12.06 | 10.5% |
| `san-juan-pr-window.tif` (2048²) | 38.3s | complete | `insufficient_ground_evidence` | 696,692 | 0.000 – 16.14 | 31.5% |
| `kahramanmaras-tr-window.tif` (2048²) | 48.1s | complete | `insufficient_ground_evidence` | 292,525 | 0.000 – 11.67 | 40.8% |

### Checks verified

- `inputFormat: "geotiff"` on all three responses.
- Geospatial metadata echo is **exact**: CRS (EPSG:32617/32619/32636), bounds, 9-value affine transform, and 0.305 m resolution all match the source rasters to within 1e-9.
- Calibration honesty: `insufficient_ground_evidence` with `heightReference: "relative"` and `heightUnit: "meters"` — no metric claims. Note the status is correct *despite ample ground pixels* (292k–1.27M): the semantic head finds ground, but without a supplied elevation value or GCPs the pipeline refuses to claim absolute heights. This is exactly the designed behavior and sets up Pass B, which supplies the missing evidence.
- All height map URLs return valid grayscale PNGs at full window resolution with plausible urban structure (10–41% nonzero coverage).
- The multitask model returned boundary + semantic outputs alongside height (`boundarySource`/`semanticSource: "trained"`) on all three.

### Findings

None blocking. One observation for ticket 05: ground pixel counts differ ~4× across scenes (Fort Myers 1.27M vs Kahramanmaras 293k of 4.2M pixels) — worth noting in the Pass B confidence analysis since calibration confidence scales with evidence count.
