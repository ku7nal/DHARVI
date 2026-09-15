# 02 — Fetch and validate Maxar test fixtures

**What to build:** Three real Maxar Open Data RGB GeoTIFF tiles are on disk and verified suitable for the pipeline, giving the verification passes real-world inputs instead of synthetic fixtures.

The tiles come from the public `maxar-opendata` S3 bucket (no authentication required):

- Fort Myers, FL (Hurricane Ian, 2022-07-23 pre-event) — dense coastal urban
- San Juan, PR (Hurricane Maria, 2017-08-29) — high-rise urban
- Kahramanmaras, Turkey (2023-02-08 pre-event) — dense low-rise urban

Tiles are stored in `kaggle/maxar-test/` in the project root, excluded from git.

**Blocked by:** None — can start immediately.

**Status:** resolved

- [x] All three tiles download into `kaggle/maxar-test/` via a repeatable documented command (plain HTTPS, no auth).
- [x] `kaggle/maxar-test/` is ignored by git.
- [x] Each tile validates against the pipeline's input contract: 3-band RGB GeoTIFF, CRS present (UTM), uint8 dtype, file size under the 256 MB upload cap.
- [x] Tile provenance (event, date, catalog ID, source URL) is recorded in the ticket comments.

## Comments

**Resolved. Three fixture windows in `kaggle/maxar-test/` (git-ignored), each validated through the pipeline's own `_read_geotiff` reader.**

### Provenance

Full 17408×17408 source tiles (kept on disk) and test windows extracted from their valid-data regions:

| Fixture | Event | Tile / Date | Catalog ID | Source URL (base `https://maxar-opendata.s3.amazonaws.com/events/`) |
|---|---|---|---|---|
| `fort-myers-fl-window.tif` (1536², 3.1 MB) | Hurricane Ian | `ard/17/031313331010/2022-10-03` | `10300100DCA2CF00` (WV02) | `Hurricane-Ian-9-26-2022/ard/17/031313331010/2022-10-03/10300100DCA2CF00-visual.tif` |
| `san-juan-pr-window.tif` (2048², 7.2 MB) | Hurricane Maria | `ard/19/122002313011/2017-08-29` | `105001000B8E2F00` | `Hurricane-Maria-PuertoRico-Oct-2017/ard/19/122002313011/2017-08-29/105001000B8E2F00-visual.tif` |
| `kahramanmaras-tr-window.tif` (2048², 8.9 MB) | Kahramanmaras earthquake | `ard/36/120022103033/2023-02-21` | `104001008314FC00` | `Kahramanmaras-turkey-earthquake-23/ard/36/120022103033/2023-02-21/104001008314FC00-visual.tif` |

Download command: `curl -fsS --retry 3 -o kaggle/maxar-test/<name>.tif "<source URL>"`

### Deviations from the original tile plan (with reasons)

1. **Fort Myers: 2022-07-23 → 2022-10-03.** The July acquisition (`10200100C8D7A600`) is WorldView-1 — panchromatic only; its "visual" product is single-band grayscale, which the pipeline rejects. The October acquisition (WV02) is true RGB.
2. **San Juan: tile `122002311230` → `122002313011`.** The original tile is only 1–2% valid pixels (footprint barely clips the grid cell); the extracted window was nearly black. The replacement tile is 100% valid, pre-event, bright urban imagery.
3. **Kahramanmaras: zone 37 / 2023-02-08 → zone 36 / 2023-02-21.** Every probed Feb-8 tile is snow-covered (mean 239–253, std < 21) — out of domain for the model. The Feb-21 acquisition has healthy urban statistics.

### Why windows, not full tiles

A full 17408² tile means ~4,500 inference tiles at 518² with 50% overlap — hours per upload on CPU. The windows (1536²–2048², ~49–81 inference tiles) keep per-upload inference in minutes. Windows are centered on the largest 512-aligned square inside each tile's valid-data region (satellite footprints cover only part of each ARD grid cell). Full tiles remain on disk as source provenance.

### Validation results (pipeline's own reader)

All three windows: accepted as `inputFormat: geotiff` — 3-band RGB, uint8, 100% valid pixels, UTM CRS preserved (EPSG:32617 / 32619 / 32636), 0.305 m resolution, well under the 256 MB cap.

### Window extraction command (repeatable)

```python
import rasterio, numpy as np
from rasterio.windows import Window
with rasterio.open("<full tile>.tif") as src:
    m = src.dataset_mask().astype(bool)
    rows, cols = np.where(m)
    r0, r1, c0, c1 = rows.min(), rows.max(), cols.min(), cols.max()
    vh, vw = r1 - r0 + 1, c1 - c0 + 1
    s = (min(2048, vh, vw) // 512) * 512
    window = Window(c0 + (vw - s) // 2, r0 + (vh - s) // 2, s, s)
    with rasterio.open("<window>.tif", "w", driver="GTiff", height=s, width=s,
                       count=src.count, dtype="uint8", crs=src.crs,
                       transform=src.window_transform(window),
                       compress="deflate", tiled=True) as dst:
        dst.write(src.read(window=window))
```

No production code changed; the backend suite still passes (46 tests).
