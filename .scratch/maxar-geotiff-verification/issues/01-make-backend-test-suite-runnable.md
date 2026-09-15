# 01 — Make the backend test suite runnable

**What to build:** The existing backend test suite executes green on this machine, so later verification work can trust the baseline. Today the suite cannot run at all because the test runner dependency is missing from the backend virtual environment, so "the GeoTIFF path works" rests on code inspection alone.

**Blocked by:** None — can start immediately.

**Status:** resolved

- [x] The backend virtual environment can run the full test suite with a single command.
- [x] All existing tests pass, including the GeoTIFF parsing, calibration, and DSM export tests, with the `dinosaur.pth` checkpoint present.
- [x] Any failures are diagnosed and either fixed or recorded as comments on this ticket before verification work proceeds.
- [x] The exact command to run the suite is documented in the ticket comments for future agents.

## Comments

**Resolved — suite was already runnable; no dependency was missing.**

The ticket's premise was wrong in a useful way: the suite does not use pytest at all. Every test module is stdlib `unittest.TestCase`, and the runner is built into Python:

```
cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

This is the same command `scripts/verify-deliverable.sh` already uses — it was the repo's canonical runner all along. The `.pytest_cache/` entry in `.gitignore` was a historical leftover. No packages were installed and no code was changed.

**Results:**
- 46 tests across 5 modules (`test_building_footprints`, `test_gamus_audit`, `test_gamus_multitask`, `test_geospatial`, `test_health`) — all pass in ~1.4s.
- GeoTIFF parsing, calibration, and DSM export tests all green, including RGB metadata preservation, RGBA acceptance, multispectral rejection, and the calibrated-metric-DSM-download test.

**Checkpoint note:** the unit suite stubs the model service (`FakeModelService` in the tests), so it never loads `dinosaur.pth`. To make the baseline trustworthy for the real-model verification passes, the real checkpoint was smoke-tested separately: `DepthAnythingModelService` loads `dinosaur.pth` successfully and returns `height`, `boundary`, and `semantic` outputs at 518×518 with plausible nonnegative value ranges. Real-model GeoTIFF uploads are exercised by tickets 03 and 04.

