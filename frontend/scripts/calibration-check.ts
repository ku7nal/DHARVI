import assert from "node:assert/strict";
import { describeCalibration } from "../src/calibration.ts";

const relative = describeCalibration("relative", { status: "insufficient_ground_evidence", method: null, confidence: 0, residualError: null, groundPixelCount: 0 });
assert.equal(relative.reference, "Estimated nDSM · relative meters");
assert.match(relative.fit, /insufficient ground evidence/);
assert.equal(relative.accuracy, null);

const calibrated = describeCalibration("absolute", {
  status: "calibrated", method: "ground_pixels_plus_ground_elevation", confidence: 0.75,
  residualError: 0.4, groundPixelCount: 100, groundElevationProvenance: "survey benchmark SB-4",
  accuracyStatus: "provenance_provided_unverified",
});
assert.equal(calibrated.reference, "Calibrated DSM · meters");
assert.match(calibrated.fit, /ground-fit residual 0.40 m/);
assert.match(calibrated.accuracy ?? "", /not independently verified/);
assert.match(calibrated.accuracy ?? "", /real-world accuracy is unverified/);

const noProvenance = describeCalibration("absolute", {
  status: "calibrated", method: "ground_pixels_plus_ground_elevation", confidence: 0.5,
  residualError: 1, groundPixelCount: 50, accuracyStatus: "unverified",
});
assert.match(noProvenance.accuracy ?? "", /accuracy is unverified/);

console.log("calibration report fixtures passed");
