import assert from "node:assert/strict";
import { getBuildingLayout } from "../src/sceneGeometry.ts";
import { DEFAULT_SCENE_LAYERS } from "../src/types.ts";

const fixtureBuilding = getBuildingLayout(4);

assert.deepEqual(fixtureBuilding, {
  wallBaseY: 0,
  wallCenterY: 2,
  roofBaseY: 4,
});

assert.deepEqual(DEFAULT_SCENE_LAYERS, {
  city: true,
  buildings: true,
  ground: true,
  roads: true,
  water: true,
  vegetation: true,
  trees: true,
  height: false,
  rgb: false,
  wireframe: false,
});

console.log("scene layout fixture passed");
