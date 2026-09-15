# 05 — Record verification evidence and file follow-ups

**What to build:** The outcome of the Maxar verification exercise is captured in one place, and anything it revealed about the GeoTIFF path is either fixed or filed — including a verdict on whether the existing "Deliver Calibrated GeoTIFF DSM Output" issue (`.scratch/final-gamus-model/issues/09`) can be considered satisfied on real-world data.

**Blocked by:** 01 — Make the backend test suite runnable; 03 — Pass A; 04 — Pass B.

**Status:** resolved

- [x] A per-tile, per-pass results summary (status, confidence, residual error, DSM validity) is appended to this ticket.
- [x] Every bug or surprise found during verification is either fixed or filed as its own ticket in the tracker.
- [x] A verdict is recorded on the acceptance criteria of the existing calibrated-GeoTIFF issue in `final-gamus-model` — satisfied, partially satisfied, or still open, with evidence.
- [x] A note on Indian-coverage test candidates (the next planned step) is recorded so that effort can start from a known point.

## Comments

**Resolved. The Maxar GeoTIFF verification exercise is complete: the pipeline works end-to-end on real-world imagery.**

### Environment

- Backend: locally running uvicorn `--reload` server (port 8000), current working tree, `dinosaur.pth` checkpoint (default)
- Model: DepthAnything-based multitask (height + boundary + semantic heads), 518² tiles, 50% overlap, CPU inference
- Baseline: 46/46 backend tests green before and after the exercise; no production code changed during tickets 02–05

### Per-tile, per-pass results

Fixtures (full provenance in ticket 02): 1536²–2048² windows extracted from Maxar Open Data ARD tiles, 3-band RGB uint8, UTM CRS, 0.305 m GSD.

**Pass A — relative nDSM, no ground evidence:**

| Fixture | Time | Prediction | Calibration status | Ground pixels | Height range (relative) | Height PNG |
|---|---|---|---|---|---|---|
| fort-myers-fl-window.tif | 19.5s | complete | `insufficient_ground_evidence` | 1,265,259 | 0–12.06 m | renders, 10.5% nonzero |
| san-juan-pr-window.tif | 38.3s | complete | `insufficient_ground_evidence` | 696,692 | 0–16.14 m | renders, 31.5% nonzero |
| kahramanmaras-tr-window.tif | 48.1s | complete | `insufficient_ground_evidence` | 292,525 | 0–11.67 m | renders, 40.8% nonzero |

Metadata echo exact on all three: `inputFormat: "geotiff"`, CRS, bounds, affine transform, resolution all match source to 1e-9. Height reference honestly labeled `relative`.

**Pass B — with ground elevation:**

| Fixture | Elev supplied | Time | Calibration | Confidence | Residual | DSM validity |
|---|---|---|---|---|---|---|
| fort-myers-fl-window.tif | 10 m | 28.6s | `calibrated` / `ground_pixels_plus_ground_elevation` | 0.9982 | 0.018 | float32, 1 band, CRS/bounds/transform exact; values 10.0–22.0 m |
| san-juan-pr-window.tif | 15 m | 74.4s | `calibrated` / `ground_pixels_plus_ground_elevation` | 0.9961 | 0.059 | float32, 1 band, CRS/bounds/transform exact; values 15.0–31.1 m |
| kahramanmaras-tr-window.tif | 550 m | 72.1s | `calibrated` / `ground_pixels_plus_ground_elevation` | 0.9999 | 0.030 | float32, 1 band, CRS/bounds/transform exact; values 550.0–561.7 m |

All Pass B responses: `heightReference: "absolute"`, downloadable DSM GeoTIFF with ground pinned at the supplied elevation and structures 10–16 m above it.

### Verdict on `.scratch/final-gamus-model/issues/09`

**Partially satisfied — issue remains open.** Recorded in full as a comment on that issue. In short: metadata preservation and DSM export are verified on real data; the user-supplied-evidence calibration path works end-to-end; the DEM/SRTM/DTM evidence source named in that issue is not implemented, and the GCP path was not exercised on real imagery. Follow-up concern about confidence semantics filed as ticket 06 below.

### Findings filed as follow-up tickets

1. **`.scratch/maxar-geotiff-verification/issues/06` — calibration confidence honesty.** Confidence (0.996–0.9999) measures internal ground-pixel consistency, not anchor accuracy; a DSM anchored to a guessed elevation still reports near-certainty. Not a test failure — a semantics gap worth fixing.
2. **`.scratch/maxar-geotiff-verification/issues/07` — upload-time variance.** Identical inputs took ~2× longer in Pass B than Pass A (e.g. 38s→74s San Juan); cause unknown, filed for investigation.

Data-selection lessons (not bugs, no tickets): Maxar ARD "visual" products from WV01 are single-band grayscale (rejected by the pipeline — by design); Feb 2023 Kahramanmaras imagery is snow-covered (out of domain); satellite footprints often cover only part of an ARD grid cell, so windows must be extracted from the valid-data region.

### Indian-coverage starting point (verified today)

The same `maxar-opendata` bucket has `events/India-Floods-Oct-2023/` with 30 ARD tiles in zone 45 (UTM 45N). Probed today: all probed tiles are 3-band RGB with two dates each (2023-02-07 pre-event, 2023-10-06 post-event). Recommended first candidate:

- `events/India-Floods-Oct-2023/ard/45/120220030330/` — **100% valid pixels** on both dates, healthy urban stats (mean 188–205, std 48–53). Sibling tiles (e.g. `120220030312`, `120220030321`) are 33–34% valid and usable with valid-region window extraction, as done for the Maxar fixtures.

Caveats for the Indian-coverage effort: Maxar event coverage is flood-focused (may be rural); if dense urban imagery is needed, probe more zone-45 tiles first (same decimated-read probing script pattern as ticket 02). For ISRO sources (Bhuvan/Bhoonidhi): Cartosat optical is panchromatic (pipeline rejects), LISS-III/IV is false-color multispectral (pipeline would accept 4-band but bands 1–3 are not RGB — model sees wrong colors), so Maxar/Sentinel-2 TCI remain the practical RGB options for Indian coverage.
