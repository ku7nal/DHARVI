import { BUILDING, GROUND, OTHERS, ROAD, WATER, createSemanticSurfaceGeometry, prepareSemanticTerrain } from "../src/semanticTerrain.ts";

const classes = Array.from({ length: 16 }, () => GROUND);
classes[5] = BUILDING;
classes[1] = WATER;
classes[10] = ROAD;
classes[15] = OTHERS;
const heights = [0, 90, 0, 0, 0, 80, 0, 0, 0, 0, 70, 0, 0, 0, 0, 0];
const terrain = prepareSemanticTerrain(heights, 4, 90, classes, 4);

if (terrain.classes[5] !== BUILDING) throw new Error("building semantic class was lost");
if (terrain.heights[5] >= heights[5]) throw new Error("building spike contaminated terrain");
if (terrain.heights[1] !== terrain.heights[0]) throw new Error("water is not stable");
if (terrain.heights[10] !== terrain.heights[0]) throw new Error("road is not stable");
if (terrain.classes[15] !== OTHERS) throw new Error("others semantic class was lost");

const isolatedBuilding = Array.from({ length: 16 }, () => GROUND);
isolatedBuilding[5] = BUILDING;
const groundGeometry = createSemanticSurfaceGeometry(terrain.heights, isolatedBuilding, 4, GROUND, 90, 1);
if (groundGeometry.getAttribute("position").count !== 20) throw new Error("ground geometry crosses the building cell");

const legacyTerrain = prepareSemanticTerrain(heights, 4, 90);
if (legacyTerrain.classes.some((classId) => classId !== GROUND)) throw new Error("height-only terrain lost its legacy ground fallback");

console.log("semantic terrain fixture passed");
