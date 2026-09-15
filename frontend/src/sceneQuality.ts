import type { BuildingRegion } from "./types";

type BuildingDetailLevel = "lod2" | "lod1" | "distant";

type SceneQualityReport = {
  fullGridCoverage: boolean;
  groundedWalls: boolean;
  flatTopBuildings: boolean;
  continuousTerrain: boolean;
  estimatedVertices: number;
  withinBrowserBudget: boolean;
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

function validateSceneQuality(heightData: number[], gridSize: number, maxHeight: number, regions: BuildingRegion[]): SceneQualityReport {
  const detailedBuildings = regions.filter((region) => getBuildingDetailLevel(region) === "lod2").length;
  const mediumBuildings = regions.filter((region) => getBuildingDetailLevel(region) === "lod1").length;
  const distantBuildings = regions.length - detailedBuildings - mediumBuildings;
  const estimatedVertices = gridSize * gridSize + regions.reduce((total, region) => total + estimateBuildingVertices(region, getBuildingDetailLevel(region)), 0);
  return {
    fullGridCoverage: heightData.length === gridSize * gridSize && gridSize >= 128,
    groundedWalls: regions.every((region) => (region.groundHeight ?? 0) >= 0 && (region.wallHeight ?? region.height) >= 0),
    flatTopBuildings: regions.every((region) => (region.footprint?.length ?? 0) >= 3 && Number.isFinite(region.wallHeight ?? region.height) && (region.wallHeight ?? region.height) >= 0),
    continuousTerrain: Number.isFinite(maxHeight) && maxHeight >= 0 && heightData.every((value) => Number.isFinite(value)),
    estimatedVertices,
    withinBrowserBudget: estimatedVertices <= 220_000,
    detailedBuildings,
    mediumBuildings,
    distantBuildings,
  };
}

export { getBuildingDetailLevel, validateSceneQuality, MAX_TREE_INSTANCES };
export type { BuildingDetailLevel, SceneQualityReport };
