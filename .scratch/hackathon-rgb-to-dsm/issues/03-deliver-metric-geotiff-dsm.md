# 03 — Deliver metric DSM output for georeferenced imagery

**What to build:** GeoTIFF uploads produce calibrated metric DSM output with preserved geospatial metadata, while ordinary images remain relative-height products.

**Blocked by:** 01 — Correct GAMUS taxonomy and retrain the final multitask checkpoint.

**Status:** ready-for-agent

- [ ] Keep PNG/JPG results explicitly marked as relative estimated nDSM output.
- [ ] Calibrate GeoTIFF predictions using ground pixels plus SRTM/DTM data or supplied ground-control points.
- [ ] Reject or flag calibration when ground evidence is insufficient.
- [ ] Export a downloadable DSM GeoTIFF with CRS, transform, bounds, resolution, and metric height values.
- [ ] Expose calibration confidence and residual error in the prediction response.
