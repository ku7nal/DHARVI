import assert from "node:assert/strict";
import { getBuildingDetailLevel, MAX_TREE_INSTANCES, validateSceneQuality } from "../src/sceneQuality.ts";
import type { BuildingRegion } from "../src/types.ts";

const region = (centerX: number): BuildingRegion => ({
  centerX, centerZ: 0, width: 0.1, depth: 0.1, height: 4, wallHeight: 3, roofRise: 1,
  roofType: "gabled", source: "fixture", footprint: [[-0.1, -0.1], [0.1, -0.1], [0.1, 0.1], [-0.1, 0.1]],
});

assert.equal(getBuildingDetailLevel(region(0.1)), "lod2");
assert.equal(getBuildingDetailLevel(region(0.5)), "lod1");
assert.equal(getBuildingDetailLevel(region(0.8)), "distant");
const report = validateSceneQuality(Array.from({ length: 256 * 256 }, () => 0), 256, 30, [region(0.1), region(0.5), region(0.8)]);
assert.equal(report.fullGridCoverage, true);
assert.equal(report.groundedWalls, true);
assert.equal(report.flatTopBuildings, true);
assert.equal(report.withinBrowserBudget, true);
assert.equal(report.finiteBuildingGeometry, true);
assert.equal(report.validBuildingPlacement, true);
assert.equal(report.fallbackSafe, true);
assert.equal(report.detailedBuildings, 1);
assert.equal(report.mediumBuildings, 1);
assert.equal(report.distantBuildings, 1);
assert.equal(MAX_TREE_INSTANCES, 512);

const malformedRegion = { ...region(0.5), centerX: Number.NaN, footprint: [[-0.1, -0.1], [Number.NaN, 0], [0.1, 0.1]] as Array<[number, number]> };
const malformedReport = validateSceneQuality(Array.from({ length: 128 * 128 }, () => 0), 128, 30, [malformedRegion]);
assert.equal(malformedReport.finiteBuildingGeometry, false);
assert.equal(malformedReport.validBuildingPlacement, false);
assert.equal(malformedReport.fallbackSafe, false);

console.log("scene quality fixture passed");
