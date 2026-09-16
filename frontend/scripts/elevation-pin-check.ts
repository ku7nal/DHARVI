import assert from "node:assert/strict";
import { clampPinPoint, formatElevationReadout, getPinHeight } from "../src/scene/elevationPin.ts";

assert.deepEqual(clampPinPoint({ row: -4, column: 99 }, 8), { row: 0, column: 7 });
assert.deepEqual(clampPinPoint({ row: 2.6, column: 3.4 }, 8), { row: 3, column: 3 });
assert.equal(getPinHeight({ row: 1, column: 2 }, [0, 1, 2, 3, 4, 5], 3), 5);
assert.equal(formatElevationReadout(12.345, "relative"), "Estimated height · 12.3 m");
assert.equal(formatElevationReadout(98.765, "absolute"), "Elevation · 98.8 m");

console.log("elevation pin fixture passed");
