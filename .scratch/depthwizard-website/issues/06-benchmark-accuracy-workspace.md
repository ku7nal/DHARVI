# 06 — Benchmark and accuracy workspace

**What to build:** Built-in GAMUS examples show RGB input, ground-truth LiDAR nDSM, predicted nDSM, error map, RMSE, MAE, and Pearson correlation while arbitrary uploads show diagnostics without unsupported accuracy claims.

**Blocked by:** 02 — Fixture-backed reconstruction upload

**Status:** resolved

- [x] The Examples navigation opens a benchmark workspace.
- [x] A benchmark example displays its RGB input.
- [x] A benchmark example displays matching ground-truth LiDAR nDSM.
- [x] A benchmark example displays the predicted nDSM.
- [x] A benchmark example displays an error map.
- [x] The benchmark view displays RMSE, MAE, and Pearson correlation.
- [x] The benchmark view clearly identifies reference-backed metrics.
- [x] Arbitrary uploads display diagnostics but no fabricated accuracy score.
- [x] Metric calculations are verified against small known arrays, including safe handling for degenerate correlation cases.
