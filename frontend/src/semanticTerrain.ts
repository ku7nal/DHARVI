import type { SemanticClass } from "./types";
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

type SemanticTerrain = {
  heights: number[];
  classes: number[];
  gridSize: number;
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

function prepareSemanticTerrain(
  heightData: number[],
  gridSize: number,
  maxHeight: number,
  semanticData?: number[] | null,
  semanticGridSize?: number | null,
): SemanticTerrain {
  const hasAlignedSemanticData = Boolean(
    semanticData?.length
      && semanticGridSize
      && Number.isInteger(semanticGridSize)
      && semanticGridSize > 0
      && semanticData.length === semanticGridSize * semanticGridSize,
  );
  const classes = hasAlignedSemanticData
    ? resizeNearest(semanticData!, semanticGridSize!, gridSize).map((value) => value >= OTHERS && value <= TREE ? value : GROUND)
    : Array.from({ length: gridSize * gridSize }, () => GROUND);
  const safeHeights = heightData.map((value) => Number.isFinite(value) ? Math.max(0, value) : 0);
  const groundHeights = safeHeights.filter((_, index) => classes[index] === GROUND);
  const nonBuildingHeights = safeHeights.filter((_, index) => classes[index] !== BUILDING);
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
          if (nextRow >= 0 && nextRow < gridSize && nextColumn >= 0 && nextColumn < gridSize && classes[nextIndex] !== BUILDING) neighbours.push(safeHeights[nextIndex]);
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
  return { heights: smoothed, classes, gridSize };
}

function createSemanticSurfaceGeometry(terrainHeights: number[], classes: number[], gridSize: number, classId: number, maxHeight: number, exaggeration: number) {
  const positions: number[] = [];
  const indices: number[] = [];
  const verticalScale = 3.6 / Math.max(maxHeight, 1) * exaggeration;
  for (let row = 0; row < gridSize; row += 1) {
    for (let column = 0; column < gridSize; column += 1) {
      const index = row * gridSize + column;
      if (classes[index] !== classId) continue;
      const base = positions.length / 3;
      const left = (column / gridSize - 0.5) * WORLD_WIDTH;
      const right = ((column + 1) / gridSize - 0.5) * WORLD_WIDTH;
      const top = (row / gridSize - 0.5) * WORLD_DEPTH;
      const bottom = ((row + 1) / gridSize - 0.5) * WORLD_DEPTH;
      const height = (terrainHeights[index] ?? 0) * verticalScale + 0.012;
      positions.push(left, height, top, right, height, top, right, height, bottom, left, height, bottom);
      indices.push(base, base + 1, base + 2, base, base + 2, base + 3);
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

function getSemanticClassColor(classId: number, semanticClasses?: Array<Pick<SemanticClass, "id" | "color">>): string {
  return semanticClasses?.find((semanticClass) => semanticClass.id === classId)?.color
    ?? SEMANTIC_TERRAIN_CLASSES.find((semanticClass) => semanticClass.id === classId)?.color
    ?? SEMANTIC_TERRAIN_CLASSES[GROUND].color;
}

export { BUILDING, GROUND, LOW_VEGETATION, OTHERS, ROAD, SEMANTIC_TERRAIN_CLASSES, TREE, WATER, createSemanticSurfaceGeometry, getSemanticClassColor, prepareSemanticTerrain };
export type { SemanticTerrain };
