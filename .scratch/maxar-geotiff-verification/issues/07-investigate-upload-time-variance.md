# 07 — Investigate upload-to-response time variance for identical inputs

**What to build:** Understand why identical GeoTIFF uploads took roughly 2× longer in Pass B than Pass A (San Juan 38s→74s, Kahramanmaras 48s→72s) on the same server and checkpoint, so demo and capacity planning can rely on predictable timings.

Calibration itself is cheap (matrix statistics over in-memory arrays), so the variance likely comes from model-load warm/cold paths, CPU contention, or memory pressure during tiled inference — but this was not investigated during the verification exercise.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] Identical uploads are timed repeatedly (≥3 runs each) with server-side timing logged around tiled inference, calibration, and asset writing.
- [ ] The dominant source of the Pass A/B variance is identified and documented in this ticket.
- [ ] If a fix is cheap (e.g. eager model load, caching), it is applied with tests; otherwise the finding is recorded for capacity planning.
