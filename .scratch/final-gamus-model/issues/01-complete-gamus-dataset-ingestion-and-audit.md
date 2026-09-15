# 01 — Complete GAMUS Dataset Ingestion and Audit

**What to build:** A Kaggle-mounted, version-pinned GAMUS dataset is verified end to end before training. The project produces a manifest covering every available split, aligned RGB/height/semantic samples, HDF5 keys, dimensions, height statistics, invalid-pixel counts, class IDs, city/source groups, and building-pixel distribution. Missing or malformed data fails visibly instead of being silently skipped.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] The complete available GAMUS release is attached to Kaggle as a read-only dataset and its exact revision or version is recorded.
- [ ] Every available train, validation, and test sample has aligned RGB, height, and semantic data with verified HDF5 keys, shapes, dtypes, and valid-pixel masks.
- [ ] The audit reports height ranges and percentiles, invalid values, class IDs, city/source groups, and building-pixel proportions.
- [ ] Missing files, unsupported shapes, invalid class IDs, spatial mismatches, and silent split omissions fail the audit with actionable errors.
- [ ] A reusable manifest is saved as a training artifact and its counts are printed before any model training begins.
