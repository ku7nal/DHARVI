import { BUILDING, GROUND, LOW_VEGETATION, OTHERS, ROAD, SEMANTIC_LAYER_DEFINITIONS, SEMANTIC_TERRAIN_CLASSES, TREE, WATER, createSemanticSurfaceGeometry, getSemanticClassColor, getVisibleSemanticClassIds, prepareSemanticTerrain, smoothSemanticClasses } from "../src/semanticTerrain.ts";
import { validSurfaceIndices } from "../src/surfaceValidity.ts";

function assertHealthyGeometry(geometry: ReturnType<typeof createSemanticSurfaceGeometry>, label: string): void {
  const positions = geometry.getAttribute("position");
  const normals = geometry.getAttribute("normal");
  if ([...positions.array, ...normals.array].some((value) => !Number.isFinite(value))) throw new Error(`${label} geometry contains a non-finite value`);
  if (Array.from({ length: normals.count }, (_, index) => normals.getY(index)).some((value) => value <= 0)) throw new Error(`${label} geometry has a downward-facing normal`);
}

function maxCellEdgeHeightDifference(geometry: ReturnType<typeof createSemanticSurfaceGeometry>): number {
  const positions = geometry.getAttribute("position");
  const index = geometry.getIndex();
  let maximum = 0;
  if (!index) return maximum;
  for (let triangle = 0; triangle < index.count; triangle += 3) {
    const firstVertex = index.getX(triangle);
    for (const offset of [1, 2]) {
      const nextVertex = index.getX(triangle + offset);
      maximum = Math.max(maximum, Math.abs(positions.getY(firstVertex) - positions.getY(nextVertex)));
    }
  }
  return maximum;
}

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

const groundedTerrain = prepareSemanticTerrain(heights, 4, 90, classes, 4, [{
  centerX: -0.125,
  centerZ: -0.125,
  width: 0.25,
  depth: 0.25,
  height: 68,
  groundHeight: 12,
  wallHeight: 56,
  roofType: "flat",
  source: "fixture",
  footprint: [[-0.25, -0.25], [0, -0.25], [0, 0], [-0.25, 0]],
  holes: [],
}]);
if (groundedTerrain.heights[5] !== 12) throw new Error("building terrain did not use the region ground height");

const greenSpikeClasses = [TREE, GROUND, GROUND, GROUND];
const greenSpikeTerrain = prepareSemanticTerrain([90, 0, 0, 0], 2, 90, greenSpikeClasses, 2);
const greenSpikeGeometry = createSemanticSurfaceGeometry(greenSpikeTerrain.heights, greenSpikeTerrain.classes, 2, TREE, 90, 1);
if (greenSpikeTerrain.heights[0] > 1 || [...greenSpikeGeometry.getAttribute("position").array].some((value, index) => index % 3 === 1 && value > 0.2)) throw new Error("green semantic spike was not suppressed");
assertHealthyGeometry(greenSpikeGeometry, "green spike");
greenSpikeGeometry.dispose();

const isolatedBuilding = Array.from({ length: 16 }, () => GROUND);
isolatedBuilding[5] = BUILDING;
const groundGeometry = createSemanticSurfaceGeometry(terrain.heights, isolatedBuilding, 4, GROUND, 90, 1);
if ((groundGeometry.getIndex()?.count ?? 0) !== 15 * 6) throw new Error("ground geometry lost cells around the building");
assertHealthyGeometry(groundGeometry, "ground");
groundGeometry.dispose();

const mixedClasses = [GROUND, ROAD, LOW_VEGETATION, WATER];
const mixedTerrain = prepareSemanticTerrain([0, 0, 0, 0], 2, 1, mixedClasses, 2);
const mixedGeometry = [GROUND, ROAD, LOW_VEGETATION, WATER].map((classId) => createSemanticSurfaceGeometry(mixedTerrain.heights, mixedTerrain.classes, 2, classId, 1, 1));
if (mixedGeometry.some((geometry) => geometry.getAttribute("position").count !== 4)) throw new Error("mixed semantic boundary lost a cell");
mixedGeometry.forEach((geometry, index) => {
  assertHealthyGeometry(geometry, `mixed class ${index}`);
  geometry.dispose();
});

const sharedEdgeHeights = [0, 10, 20, 30];
const groundEdge = createSemanticSurfaceGeometry(sharedEdgeHeights, mixedClasses, 2, GROUND, 30, 1).getAttribute("position");
const roadEdge = createSemanticSurfaceGeometry(sharedEdgeHeights, mixedClasses, 2, ROAD, 30, 1).getAttribute("position");
if (groundEdge.getY(1) !== roadEdge.getY(0) || groundEdge.getY(2) !== roadEdge.getY(3)) throw new Error("semantic boundary heights are not continuous");
const stableRoad = createSemanticSurfaceGeometry(sharedEdgeHeights, mixedClasses, 2, ROAD, 30, 1, 0).getAttribute("position");
if ([...stableRoad.array].some((value, index) => index % 3 === 1 && Math.abs(value - 0.012) > 0.0001)) throw new Error("road geometry was not held at the terrain baseline");
const stableWater = createSemanticSurfaceGeometry(sharedEdgeHeights, mixedClasses, 2, WATER, 30, 1, 0).getAttribute("position");
if ([...stableWater.array].some((value, index) => index % 3 === 1 && Math.abs(value - 0.012) > 0.0001)) throw new Error("water geometry was not held at the terrain baseline");

const reliefTerrain = prepareSemanticTerrain([0, 10, 20, 30], 2, 30, [GROUND, GROUND, GROUND, GROUND], 2);
const reliefGeometry = createSemanticSurfaceGeometry(reliefTerrain.heights, reliefTerrain.classes, 2, GROUND, 30, 1);
assertHealthyGeometry(reliefGeometry, "relief");
if (Math.max(...reliefTerrain.heights) - Math.min(...reliefTerrain.heights) <= 0) throw new Error("broad terrain relief was flattened");
if (maxCellEdgeHeightDifference(reliefGeometry) > 1.25) throw new Error("local semantic height difference exceeded the smoothing threshold");
reliefGeometry.dispose();

const expectedPalette = ["#d9d9d9", "#b6c99e", "#83a96f", "#c7cbd1", "#72aee8", "#e8e1d6", "#4f8258"];
for (const [classId, expectedColor] of expectedPalette.entries()) {
  if (SEMANTIC_TERRAIN_CLASSES.find(({ id }) => id === classId)?.color !== expectedColor) throw new Error(`semantic palette mismatch for class ${classId}`);
}
if (getSemanticClassColor(ROAD, [{ id: ROAD, color: "#123456" }]) !== "#123456") throw new Error("prediction palette was ignored");
if (getSemanticClassColor(99) !== "#b6c99e") throw new Error("unknown palette class has no safe fallback");

const allSemanticLayers = { buildings: true, ground: true, roads: true, water: true, vegetation: true, trees: true };
const allVisibleClassIds = getVisibleSemanticClassIds(allSemanticLayers);
if (allVisibleClassIds.length !== SEMANTIC_LAYER_DEFINITIONS.length || new Set(allVisibleClassIds).size !== allVisibleClassIds.length) throw new Error("semantic layer mapping is incomplete");
for (const definition of SEMANTIC_LAYER_DEFINITIONS) {
  if (!definition.layer) continue;
  const visibleWithLayerDisabled = getVisibleSemanticClassIds({ ...allSemanticLayers, [definition.layer]: false });
  if (visibleWithLayerDisabled.includes(definition.classId)) throw new Error(`layer toggle did not hide class ${definition.classId}`);
  if (visibleWithLayerDisabled.length !== allVisibleClassIds.length - 1) throw new Error(`layer toggle affected unrelated classes for ${definition.layer}`);
}

const invalidTerrain = prepareSemanticTerrain([0, 0, 0, 0], 2, 1, [99, -1, Number.NaN, GROUND], 2);
if (invalidTerrain.classes.join(",") !== `${GROUND},${GROUND},${GROUND},${GROUND}`) throw new Error("invalid semantic class was not safely normalized");

const noisyClasses = Array.from({ length: 25 }, () => GROUND);
noisyClasses[12] = LOW_VEGETATION;
noisyClasses[0] = ROAD;
const smoothedClasses = smoothSemanticClasses(noisyClasses, 5);
if (smoothedClasses[12] !== GROUND || smoothedClasses[0] !== ROAD) throw new Error("non-road speckles were not cleaned without changing roads");

const roadCorridor = Array.from({ length: 25 }, (_, index) => index >= 10 && index < 15 ? ROAD : GROUND);
if (smoothSemanticClasses(roadCorridor, 5).slice(10, 15).some((classId) => classId !== ROAD)) throw new Error("road corridor was altered by semantic smoothing");

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
  const indices = geometry.getIndex()?.count ?? 0;
  if (indices % 6 !== 0) throw new Error("semantic geometry has an invalid tile shape");
  assertHealthyGeometry(geometry, "256x256 semantic");
  geometry.dispose();
  return total + indices / 6;
}, 0);
if (budgetGeometries.length !== expectedPalette.length || totalBudgetCells !== budgetGridSize ** 2) throw new Error("semantic geometry budget is not bounded to one tile per cell");

const legacyTerrain = prepareSemanticTerrain(heights, 4, 90);
if (legacyTerrain.classes.some((classId) => classId !== GROUND)) throw new Error("height-only terrain lost its legacy ground fallback");

const maskedTerrain = prepareSemanticTerrain([80, 0, 80, 0], 2, 80, [GROUND, GROUND, GROUND, GROUND], 2, undefined, [true, false, true, false]);
const maskedGeometry = createSemanticSurfaceGeometry(maskedTerrain.heights, maskedTerrain.classes, 2, GROUND, 80, 1);
if (maskedTerrain.baseHeight !== 80 || maskedTerrain.classes[1] !== -1 || (maskedGeometry.getIndex()?.count ?? 0) !== 12) throw new Error("nodata cells affected semantic terrain or remained rendered");
maskedGeometry.dispose();
if (validSurfaceIndices([0, 1, 2, 2, 1, 3], [true, true, true, false]).join(",") !== "0,1,2") throw new Error("terrain mesh retained a triangle that touches nodata");

console.log("semantic terrain fixture passed");
