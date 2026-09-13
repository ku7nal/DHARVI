import { BUILDING, GROUND, LOW_VEGETATION, OTHERS, ROAD, SEMANTIC_TERRAIN_CLASSES, TREE, WATER, createSemanticSurfaceGeometry, getSemanticClassColor, prepareSemanticTerrain } from "../src/semanticTerrain.ts";

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
if (groundGeometry.getAttribute("position").count !== 15 * 4) throw new Error("ground geometry lost cells around the building");
if ((groundGeometry.getAttribute("normal").getY(0) ?? 0) <= 0) throw new Error("semantic surface normal points away from the scene");

const mixedClasses = [GROUND, ROAD, LOW_VEGETATION, WATER];
const mixedTerrain = prepareSemanticTerrain([0, 0, 0, 0], 2, 1, mixedClasses, 2);
const mixedGeometry = [GROUND, ROAD, LOW_VEGETATION, WATER].map((classId) => createSemanticSurfaceGeometry(mixedTerrain.heights, mixedTerrain.classes, 2, classId, 1, 1));
if (mixedGeometry.some((geometry) => geometry.getAttribute("position").count !== 4)) throw new Error("mixed semantic boundary lost a cell");

const expectedPalette = ["#d9d9d9", "#b6c99e", "#83a96f", "#c7cbd1", "#72aee8", "#e8e1d6", "#4f8258"];
for (const [classId, expectedColor] of expectedPalette.entries()) {
  if (SEMANTIC_TERRAIN_CLASSES.find(({ id }) => id === classId)?.color !== expectedColor) throw new Error(`semantic palette mismatch for class ${classId}`);
}
if (getSemanticClassColor(ROAD, [{ id: ROAD, color: "#123456" }]) !== "#123456") throw new Error("prediction palette was ignored");
if (getSemanticClassColor(99) !== "#b6c99e") throw new Error("unknown palette class has no safe fallback");

const invalidTerrain = prepareSemanticTerrain([0, 0, 0, 0], 2, 1, [99, -1, Number.NaN, GROUND], 2);
if (invalidTerrain.classes.join(",") !== `${GROUND},${GROUND},${GROUND},${GROUND}`) throw new Error("invalid semantic class was not safely normalized");

const resizedTerrain = prepareSemanticTerrain(Array.from({ length: 16 }, () => 0), 4, 1, [ROAD, LOW_VEGETATION, LOW_VEGETATION, ROAD], 2);
if (resizedTerrain.gridSize !== 4 || resizedTerrain.classes.length !== 4 ** 2) throw new Error("semantic data was not aligned to the scene grid");
if (resizedTerrain.classes[0] !== ROAD || resizedTerrain.classes[3] !== LOW_VEGETATION || resizedTerrain.classes[12] !== LOW_VEGETATION || resizedTerrain.classes[15] !== ROAD) throw new Error("semantic grid resize lost alignment");

const budgetGridSize = 256;
const budgetTerrain = prepareSemanticTerrain(
  Array.from({ length: budgetGridSize ** 2 }, () => 0),
  budgetGridSize,
  1,
  Array.from({ length: budgetGridSize ** 2 }, (_, index) => index % expectedPalette.length),
  budgetGridSize,
);
const budgetGeometries = [OTHERS, GROUND, LOW_VEGETATION, BUILDING, WATER, ROAD, TREE].map((classId) => createSemanticSurfaceGeometry(budgetTerrain.heights, budgetTerrain.classes, budgetGridSize, classId, 1, 1));
const totalBudgetCells = budgetGeometries.reduce((total, geometry) => {
  const positions = geometry.getAttribute("position").count;
  const indices = geometry.getIndex()?.count ?? 0;
  if (positions % 4 !== 0 || indices % 6 !== 0) throw new Error("semantic geometry has an invalid tile shape");
  geometry.dispose();
  return total + positions / 4;
}, 0);
if (budgetGeometries.length !== expectedPalette.length || totalBudgetCells !== budgetGridSize ** 2) throw new Error("semantic geometry budget is not bounded to one tile per cell");

const legacyTerrain = prepareSemanticTerrain(heights, 4, 90);
if (legacyTerrain.classes.some((classId) => classId !== GROUND)) throw new Error("height-only terrain lost its legacy ground fallback");

console.log("semantic terrain fixture passed");
