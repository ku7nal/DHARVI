import assert from "node:assert/strict";
import type { BuildingRegion } from "../src/types.ts";
import { createBuildingExtrusionGeometry, createRoofGeometry } from "../src/buildingGeometry.ts";

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

const irregularRegion: BuildingRegion = {
  ...region,
  footprint: [[-0.2, -0.15], [0.05, -0.15], [0.05, -0.03], [0.2, -0.03], [0.2, 0.15], [-0.2, 0.15]],
};
const irregularGeometry = createBuildingExtrusionGeometry(irregularRegion, 1, 15, 11);
assert.ok(irregularGeometry);
irregularGeometry.computeBoundingBox();
assert.ok(irregularGeometry.boundingBox);
assert.ok(irregularGeometry.getAttribute("position").count > geometry.getAttribute("position").count);
irregularGeometry.dispose();

const gabledRoof = createRoofGeometry(region, 1, 15, 11);
assert.ok(gabledRoof);
gabledRoof.computeBoundingBox();
assert.ok(gabledRoof.boundingBox);
assert.ok(Math.abs(gabledRoof.boundingBox.min.y - 3) < 1e-6);
assert.ok(gabledRoof.boundingBox.max.y > 3.9);
gabledRoof.dispose();

const steppedRoof = createRoofGeometry({ ...region, roofType: "stepped", roofRise: 0.8 }, 1, 15, 11);
assert.ok(steppedRoof);
steppedRoof.computeBoundingBox();
assert.ok(steppedRoof.boundingBox && steppedRoof.boundingBox.max.y > 3.3);
steppedRoof.dispose();

assert.equal(createRoofGeometry({ ...region, roofType: "flat" }, 1, 15, 11), null);
assert.equal(createRoofGeometry({ ...region, footprint: [[-0.2, -0.15], [0.05, -0.15], [0.05, -0.03], [0.2, -0.03], [0.2, 0.15], [-0.2, 0.15]] }, 1, 15, 11), null);

console.log("building extrusion geometry fixture passed");
