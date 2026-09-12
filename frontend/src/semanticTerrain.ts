import type { SemanticClass } from "./types";

const GROUND = 0;
const LOW_VEGETATION = 1;
const BUILDING = 2;
const WATER = 3;
const ROAD = 4;
const TREE = 5;

type SemanticTerrain = {
  heights: number[];
  classes: number[];
  gridSize: number;
};

function resizeNearest(values: number[], sourceSize: number, targetSize: number): number[] {
  if (sourceSize === targetSize) return [...values];
  return Array.from({ length: targetSize * targetSize }, (_, index) => {
    const row = Math.min(sourceSize - 1, Math.floor(index / targetSize * sourceSize));
    const column = Math.min(sourceSize - 1, Math.floor(index % targetSize / targetSize * sourceSize));
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
  const classes = semanticData?.length && semanticGridSize
    ? resizeNearest(semanticData, semanticGridSize, gridSize).map((value) => value >= GROUND && value <= TREE ? value : GROUND)
    : Array.from({ length: gridSize * gridSize }, () => GROUND);
  const safeHeights = heightData.map((value) => Number.isFinite(value) ? Math.max(0, value) : 0);
  const nonBuildingHeights = safeHeights.filter((_, index) => classes[index] !== BUILDING);
  const baseHeight = median(nonBuildingHeights, 0);
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
      if (nextRow >= 0 && nextRow < gridSize && nextColumn >= 0 && nextColumn < gridSize && classes[nextIndex] !== BUILDING) neighbours.push(terrainHeights[nextIndex]);
    }
    return median(neighbours, value);
  });
  return { heights: smoothed, classes, gridSize };
}

const SEMANTIC_TERRAIN_CLASSES: Array<Pick<SemanticClass, "id" | "name" | "color">> = [
  { id: GROUND, name: "ground", color: "#b6c99e" },
  { id: LOW_VEGETATION, name: "low_vegetation", color: "#83a96f" },
  { id: WATER, name: "water", color: "#72aee8" },
  { id: ROAD, name: "road", color: "#e8e1d6" },
  { id: TREE, name: "tree", color: "#4f8258" },
];

export { BUILDING, GROUND, LOW_VEGETATION, ROAD, SEMANTIC_TERRAIN_CLASSES, TREE, WATER, prepareSemanticTerrain };
export type { SemanticTerrain };
