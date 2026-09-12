import { BUILDING, GROUND, ROAD, WATER, createSemanticSurfaceGeometry, prepareSemanticTerrain } from "../src/semanticTerrain.ts";

const classes = Array.from({ length: 16 }, () => GROUND);
classes[5] = BUILDING;
classes[1] = WATER;
classes[10] = ROAD;
const heights = [0, 90, 0, 0, 0, 80, 0, 0, 0, 0, 70, 0, 0, 0, 0, 0];
const terrain = prepareSemanticTerrain(heights, 4, 90, classes, 4);

if (terrain.classes[5] !== BUILDING) throw new Error("building semantic class was lost");
if (terrain.heights[5] >= heights[5]) throw new Error("building spike contaminated terrain");
if (terrain.heights[1] !== terrain.heights[0]) throw new Error("water is not stable");
if (terrain.heights[10] !== terrain.heights[0]) throw new Error("road is not stable");

const isolatedBuilding = Array.from({ length: 16 }, () => GROUND);
isolatedBuilding[5] = BUILDING;
const groundGeometry = createSemanticSurfaceGeometry(terrain.heights, isolatedBuilding, 4, GROUND, 90, 1);
if (groundGeometry.getAttribute("position").count !== 20) throw new Error("ground geometry crosses the building cell");

console.log("semantic terrain fixture passed");
