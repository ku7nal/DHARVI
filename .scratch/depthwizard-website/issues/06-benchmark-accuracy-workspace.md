# 06 — Benchmark and accuracy workspace

**What to build:** Built-in GAMUS examples show RGB input, ground-truth LiDAR nDSM, predicted nDSM, error map, RMSE, MAE, and Pearson correlation while arbitrary uploads show diagnostics without unsupported accuracy claims.

**Blocked by:** 02 — Fixture-backed reconstruction upload

**Status:** ready-for-agent

- [ ] The Examples navigation opens a benchmark workspace.
- [ ] A benchmark example displays its RGB input.
- [ ] A benchmark example displays matching ground-truth LiDAR nDSM.
- [ ] A benchmark example displays the predicted nDSM.
- [ ] A benchmark example displays an error map.
- [ ] The benchmark view displays RMSE, MAE, and Pearson correlation.
- [ ] The benchmark view clearly identifies reference-backed metrics.
- [ ] Arbitrary uploads display diagnostics but no fabricated accuracy score.
- [ ] Metric calculations are verified against small known arrays, including safe handling for degenerate correlation cases.
