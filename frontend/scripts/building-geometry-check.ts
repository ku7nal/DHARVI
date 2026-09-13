import assert from "node:assert/strict";
import type { BuildingRegion } from "../src/types.ts";
import { createBuildingExtrusionGeometry } from "../src/buildingGeometry.ts";

const region: BuildingRegion = {
  centerX: 0,
  centerZ: 0,
  width: 0.4,
  depth: 0.3,
  height: 4,
  wallHeight: 3,
  roofType: "gabled",
  roofRise: 1,
  source: "fixture",
  footprint: [[-0.2, -0.15], [0.2, -0.15], [0.2, 0.15], [-0.2, 0.15]],
};

const geometry = createBuildingExtrusionGeometry(region, 1, 15, 11);
assert.ok(geometry);
assert.ok(geometry.getAttribute("normal"));
geometry.computeBoundingBox();
assert.ok(geometry.boundingBox);
assert.ok(Math.abs(geometry.boundingBox.min.y) < 1e-6);
assert.ok(Math.abs(geometry.boundingBox.max.y - 3) < 1e-6);

console.log("building extrusion geometry fixture passed");
