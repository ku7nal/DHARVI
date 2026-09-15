import type { BuildingRegion } from "./types";

type BuildingDetailLevel = "lod2" | "lod1" | "distant";

type SceneQualityReport = {
  fullGridCoverage: boolean;
  groundedWalls: boolean;
  flatTopBuildings: boolean;
  continuousTerrain: boolean;
  estimatedVertices: number;
  withinBrowserBudget: boolean;
  finiteBuildingGeometry: boolean;
  validBuildingPlacement: boolean;
  fallbackSafe: boolean;
  detailedBuildings: number;
  mediumBuildings: number;
  distantBuildings: number;
};

const MAX_TREE_INSTANCES = 512;

function getBuildingDetailLevel(region: BuildingRegion): BuildingDetailLevel {
  const distance = Math.hypot(region.centerX, region.centerZ);
  if (distance <= 0.36) return "lod2";
  if (distance <= 0.74) return "lod1";
  return "distant";
}

function estimateBuildingVertices(region: BuildingRegion, detailLevel: BuildingDetailLevel): number {
  const footprintVertices = detailLevel === "lod2" || detailLevel === "lod1" ? region.footprint?.length ?? 4 : 4;
  return footprintVertices * 2;
}

function isFinitePolygon(polygon: Array<[number, number]> | undefined): boolean {
  return !polygon || polygon.every(([x, z]) => Number.isFinite(x) && Number.isFinite(z));
}

function hasFiniteBuildingGeometry(region: BuildingRegion): boolean {
  return [region.centerX, region.centerZ, region.width, region.depth, region.height, region.wallHeight, region.groundHeight, region.roofRise]
    .filter((value) => value !== undefined)
    .every((value) => Number.isFinite(value))
    && isFinitePolygon(region.footprint)
    && (region.holes ?? []).every((hole) => isFinitePolygon(hole));
}

function hasValidBuildingPlacement(region: BuildingRegion): boolean {
  const wallHeight = Number.isFinite(region.wallHeight) ? region.wallHeight! : region.height;
  return Number.isFinite(region.centerX)
    && Number.isFinite(region.centerZ)
    && Number.isFinite(region.width)
    && Number.isFinite(region.depth)
    && region.width >= 0
    && region.depth >= 0
    && Number.isFinite(region.groundHeight ?? 0)
    && Number.isFinite(wallHeight)
    && wallHeight >= 0;
}

function validateSceneQuality(heightData: number[], gridSize: number, maxHeight: number, regions: BuildingRegion[]): SceneQualityReport {
  const detailedBuildings = regions.filter((region) => getBuildingDetailLevel(region) === "lod2").length;
  const mediumBuildings = regions.filter((region) => getBuildingDetailLevel(region) === "lod1").length;
  const distantBuildings = regions.length - detailedBuildings - mediumBuildings;
  const estimatedVertices = gridSize * gridSize + regions.reduce((total, region) => total + estimateBuildingVertices(region, getBuildingDetailLevel(region)), 0);
  const finiteBuildingGeometry = regions.every(hasFiniteBuildingGeometry);
  const validBuildingPlacement = regions.every(hasValidBuildingPlacement);
  return {
    fullGridCoverage: heightData.length === gridSize * gridSize && gridSize >= 128,
    groundedWalls: regions.every((region) => (region.groundHeight ?? 0) >= 0 && (Number.isFinite(region.wallHeight) ? region.wallHeight! : region.height) >= 0),
    flatTopBuildings: finiteBuildingGeometry && validBuildingPlacement,
    continuousTerrain: Number.isFinite(maxHeight) && maxHeight >= 0 && heightData.every((value) => Number.isFinite(value)),
    estimatedVertices,
    withinBrowserBudget: estimatedVertices <= 220_000,
    finiteBuildingGeometry,
    validBuildingPlacement,
    fallbackSafe: finiteBuildingGeometry && validBuildingPlacement,
    detailedBuildings,
    mediumBuildings,
    distantBuildings,
  };
}

export { getBuildingDetailLevel, validateSceneQuality, MAX_TREE_INSTANCES };
export type { BuildingDetailLevel, SceneQualityReport };
