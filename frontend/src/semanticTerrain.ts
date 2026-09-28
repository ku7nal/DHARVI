import type { BuildingRegion, SemanticClass } from "./types";
import * as THREE from "three";

const WORLD_WIDTH = 15;
const WORLD_DEPTH = 11;

const OTHERS = 0;
const GROUND = 1;
const LOW_VEGETATION = 2;
const BUILDING = 3;
const WATER = 4;
const ROAD = 5;
const TREE = 6;

type SemanticLayerName = "buildings" | "ground" | "roads" | "water" | "vegetation" | "trees";

type SemanticTerrain = {
  heights: number[];
  classes: number[];
  gridSize: number;
  baseHeight: number;
};

function resizeNearest(values: number[], sourceSize: number, targetSize: number): number[] {
  if (sourceSize === targetSize) return [...values];
  return Array.from({ length: targetSize * targetSize }, (_, index) => {
    const targetRow = Math.floor(index / targetSize);
    const targetColumn = index % targetSize;
    const row = Math.min(sourceSize - 1, Math.floor(targetRow / targetSize * sourceSize));
    const column = Math.min(sourceSize - 1, Math.floor(targetColumn / targetSize * sourceSize));
    return values[row * sourceSize + column] ?? GROUND;
  });
}

function median(values: number[], fallback: number): number {
  if (!values.length) return fallback;
  const sorted = [...values].sort((left, right) => left - right);
  return sorted[Math.floor(sorted.length / 2)];
}

function pointInPolygon(x: number, z: number, polygon: Array<[number, number]>): boolean {
  let inside = false;
  for (let index = 0, previous = polygon.length - 1; index < polygon.length; previous = index, index += 1) {
    const [currentX, currentZ] = polygon[index];
    const [previousX, previousZ] = polygon[previous];
    const intersects = (currentZ > z) !== (previousZ > z)
      && x < (previousX - currentX) * (z - currentZ) / (previousZ - currentZ) + currentX;
    if (intersects) inside = !inside;
  }
  return inside;
}

function regionContainsCell(region: BuildingRegion, x: number, z: number): boolean {
  if (!region.footprint || region.footprint.length < 3 || !pointInPolygon(x, z, region.footprint)) return false;
  return !(region.holes ?? []).some((hole) => hole.length >= 3 && pointInPolygon(x, z, hole));
}

function smoothSemanticClasses(classes: number[], gridSize: number): number[] {
  const smoothed = [...classes];
  const smoothable = new Set([GROUND, LOW_VEGETATION, OTHERS]);
  const protectedClasses = new Set([BUILDING, WATER, ROAD, TREE]);
  for (let pass = 0; pass < 2; pass += 1) {
    const source = [...smoothed];
    for (let row = 0; row < gridSize; row += 1) {
      for (let column = 0; column < gridSize; column += 1) {
        const index = row * gridSize + column;
        const currentClass = source[index];
        if (!smoothable.has(currentClass) || protectedClasses.has(currentClass)) continue;
        const counts = new Map<number, number>();
        for (let rowDelta = -1; rowDelta <= 1; rowDelta += 1) {
          for (let columnDelta = -1; columnDelta <= 1; columnDelta += 1) {
            if (rowDelta === 0 && columnDelta === 0) continue;
            const nextRow = row + rowDelta;
            const nextColumn = column + columnDelta;
            if (nextRow < 0 || nextRow >= gridSize || nextColumn < 0 || nextColumn >= gridSize) continue;
            const neighbourClass = source[nextRow * gridSize + nextColumn];
            if (!smoothable.has(neighbourClass)) continue;
            counts.set(neighbourClass, (counts.get(neighbourClass) ?? 0) + 1);
          }
        }
        const groundCount = counts.get(GROUND) ?? 0;
        const vegetationCount = counts.get(LOW_VEGETATION) ?? 0;
        const targetClass = groundCount >= vegetationCount ? GROUND : LOW_VEGETATION;
        const targetCount = Math.max(groundCount, vegetationCount);
        if (targetClass !== currentClass && targetCount >= 6) smoothed[index] = targetClass;
      }
    }
  }
  return smoothed;
}

function prepareSemanticTerrain(
  heightData: number[],
  gridSize: number,
  maxHeight: number,
  semanticData?: number[] | null,
  semanticGridSize?: number | null,
  buildingRegions?: readonly BuildingRegion[],
  validityData?: readonly boolean[] | null,
): SemanticTerrain {
  const hasAlignedSemanticData = Boolean(
    semanticData?.length
      && semanticGridSize
      && Number.isInteger(semanticGridSize)
      && semanticGridSize > 0
      && semanticData.length === semanticGridSize * semanticGridSize,
  );
  const normalizedClasses = hasAlignedSemanticData
    ? resizeNearest(semanticData!, semanticGridSize!, gridSize).map((value) => value >= OTHERS && value <= TREE ? value : GROUND)
    : Array.from({ length: gridSize * gridSize }, () => GROUND);
  if (validityData?.length === gridSize * gridSize) {
    normalizedClasses.forEach((_, index) => { if (!validityData[index]) normalizedClasses[index] = -1; });
  }
  const classes = smoothSemanticClasses(normalizedClasses, gridSize);
  const safeHeights = heightData.map((value) => Number.isFinite(value) ? Math.max(0, value) : 0);
  const groundHeights = safeHeights.filter((_, index) => classes[index] === GROUND);
  const nonBuildingHeights = safeHeights.filter((_, index) => classes[index] >= 0 && classes[index] !== BUILDING);
  const baseHeight = median(groundHeights.length ? groundHeights : nonBuildingHeights, 0);
  const terrainHeights = safeHeights.map((value, index) => {
    const semanticClass = classes[index];
    if (semanticClass === BUILDING) {
      const row = Math.floor(index / gridSize);
      const column = index % gridSize;
      const neighbours: number[] = [];
      for (let rowDelta = -1; rowDelta <= 1; rowDelta += 1) {
        for (let columnDelta = -1; columnDelta <= 1; columnDelta += 1) {
          const nextRow = row + rowDelta;
          const nextColumn = column + columnDelta;
          const nextIndex = nextRow * gridSize + nextColumn;
          if (nextRow >= 0 && nextRow < gridSize && nextColumn >= 0 && nextColumn < gridSize && classes[nextIndex] >= 0 && classes[nextIndex] !== BUILDING) neighbours.push(safeHeights[nextIndex]);
        }
      }
      return median(neighbours, baseHeight);
    }
    if (semanticClass === WATER || semanticClass === ROAD) return baseHeight;
    return Math.min(value, baseHeight + Math.max(maxHeight * 0.08, 0.5));
  });

  const smoothed = terrainHeights.map((value, index) => {
    if (classes[index] === BUILDING) return value;
    const row = Math.floor(index / gridSize);
    const column = index % gridSize;
    const neighbours = [value];
    for (const [rowDelta, columnDelta] of [[-1, 0], [1, 0], [0, -1], [0, 1]]) {
      const nextRow = row + rowDelta;
      const nextColumn = column + columnDelta;
      const nextIndex = nextRow * gridSize + nextColumn;
      if (nextRow >= 0 && nextRow < gridSize && nextColumn >= 0 && nextColumn < gridSize && classes[nextIndex] === classes[index]) neighbours.push(terrainHeights[nextIndex]);
    }
    return classes[index] === WATER || classes[index] === ROAD ? baseHeight : median(neighbours, value);
  });
  const groundedBuildingHeights = smoothed.map((value, index) => {
    if (classes[index] !== BUILDING || !buildingRegions?.length) return value;
    const row = Math.floor(index / gridSize);
    const column = index % gridSize;
    const x = (column + 0.5) / gridSize - 0.5;
    const z = (row + 0.5) / gridSize - 0.5;
    const region = buildingRegions.find((candidate) => Number.isFinite(candidate.groundHeight) && regionContainsCell(candidate, x, z));
    return region?.groundHeight ?? value;
  });
  const spikeSuppressedHeights = groundedBuildingHeights.map((value, index) => {
    if (classes[index] !== LOW_VEGETATION && classes[index] !== TREE) return value;
    const row = Math.floor(index / gridSize);
    const column = index % gridSize;
    const neighbours: number[] = [];
    for (let rowDelta = -1; rowDelta <= 1; rowDelta += 1) {
      for (let columnDelta = -1; columnDelta <= 1; columnDelta += 1) {
        const nextRow = row + rowDelta;
        const nextColumn = column + columnDelta;
        const nextIndex = nextRow * gridSize + nextColumn;
        if (nextRow < 0 || nextRow >= gridSize || nextColumn < 0 || nextColumn >= gridSize) continue;
        if (classes[nextIndex] === BUILDING || classes[nextIndex] === ROAD || classes[nextIndex] === WATER) continue;
        neighbours.push(groundedBuildingHeights[nextIndex]);
      }
    }
    return median(neighbours, value);
  });
  return { heights: spikeSuppressedHeights, classes, gridSize, baseHeight };
}

function createSemanticSurfaceGeometry(terrainHeights: number[], classes: number[], gridSize: number, classId: number, maxHeight: number, exaggeration: number, stableHeight?: number) {
  const positions: number[] = [];
  const indices: number[] = [];
  const vertexIndices = new Map<string, number>();
  const verticalScale = 3.6 / Math.max(maxHeight, 1) * exaggeration;
  const isStableVertex = (row: number, column: number) => {
    if (!Number.isFinite(stableHeight)) return false;
    for (const rowDelta of [-1, 0]) {
      for (const columnDelta of [-1, 0]) {
        const cellRow = row + rowDelta;
        const cellColumn = column + columnDelta;
        if (cellRow < 0 || cellRow >= gridSize || cellColumn < 0 || cellColumn >= gridSize) continue;
        const cellClass = classes[cellRow * gridSize + cellColumn];
        if (cellClass === ROAD || cellClass === WATER) return true;
      }
    }
    return false;
  };
  const heightAtVertex = (row: number, column: number) => {
    const safeRow = Math.max(0, Math.min(gridSize - 1, row));
    const safeColumn = Math.max(0, Math.min(gridSize - 1, column));
    const index = safeRow * gridSize + safeColumn;
    const height = isStableVertex(row, column)
      ? stableHeight!
      : terrainHeights[index] ?? 0;
    return height * verticalScale + 0.012;
  };
  const vertexAt = (row: number, column: number) => {
    const key = `${row}:${column}`;
    const existing = vertexIndices.get(key);
    if (existing !== undefined) return existing;
    const index = positions.length / 3;
    const x = (column / gridSize - 0.5) * WORLD_WIDTH;
    const z = (row / gridSize - 0.5) * WORLD_DEPTH;
    positions.push(x, heightAtVertex(row, column), z);
    vertexIndices.set(key, index);
    return index;
  };
  for (let row = 0; row < gridSize; row += 1) {
    for (let column = 0; column < gridSize; column += 1) {
      const index = row * gridSize + column;
      if (classes[index] !== classId) continue;
      const bottomLeft = vertexAt(row + 1, column);
      const bottomRight = vertexAt(row + 1, column + 1);
      const topRight = vertexAt(row, column + 1);
      const topLeft = vertexAt(row, column);
      indices.push(bottomLeft, bottomRight, topRight, bottomLeft, topRight, topLeft);
    }
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}

const SEMANTIC_TERRAIN_CLASSES: Array<Pick<SemanticClass, "id" | "name" | "color">> = [
  { id: OTHERS, name: "others", color: "#d9d9d9" },
  { id: GROUND, name: "ground", color: "#b6c99e" },
  { id: LOW_VEGETATION, name: "low_vegetation", color: "#83a96f" },
  { id: BUILDING, name: "building", color: "#c7cbd1" },
  { id: WATER, name: "water", color: "#72aee8" },
  { id: ROAD, name: "road", color: "#e8e1d6" },
  { id: TREE, name: "tree", color: "#4f8258" },
];

const SEMANTIC_LAYER_DEFINITIONS: ReadonlyArray<{ classId: number; layer: SemanticLayerName | null }> = [
  { classId: OTHERS, layer: null },
  { classId: GROUND, layer: "ground" },
  { classId: LOW_VEGETATION, layer: "vegetation" },
  { classId: BUILDING, layer: "buildings" },
  { classId: WATER, layer: "water" },
  { classId: ROAD, layer: "roads" },
  { classId: TREE, layer: "trees" },
];

function getVisibleSemanticClassIds(layers: Readonly<Record<SemanticLayerName, boolean>>): number[] {
  return SEMANTIC_LAYER_DEFINITIONS
    .filter(({ layer }) => layer === null || layers[layer])
    .map(({ classId }) => classId);
}

function getSemanticClassColor(classId: number, semanticClasses?: Array<Pick<SemanticClass, "id" | "color">>): string {
  return semanticClasses?.find((semanticClass) => semanticClass.id === classId)?.color
    ?? SEMANTIC_TERRAIN_CLASSES.find((semanticClass) => semanticClass.id === classId)?.color
    ?? SEMANTIC_TERRAIN_CLASSES[GROUND].color;
}

export { BUILDING, GROUND, LOW_VEGETATION, OTHERS, ROAD, SEMANTIC_LAYER_DEFINITIONS, SEMANTIC_TERRAIN_CLASSES, TREE, WATER, createSemanticSurfaceGeometry, getSemanticClassColor, getVisibleSemanticClassIds, prepareSemanticTerrain, smoothSemanticClasses };
export type { SemanticTerrain };
