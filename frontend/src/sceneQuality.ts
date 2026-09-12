import type { BuildingRegion } from "./types";

type BuildingDetailLevel = "lod2" | "distant";

type SceneQualityReport = {
  fullGridCoverage: boolean;
  groundedWalls: boolean;
  sharpRoofs: boolean;
  continuousTerrain: boolean;
  estimatedVertices: number;
  withinBrowserBudget: boolean;
  detailedBuildings: number;
  distantBuildings: number;
};

function getBuildingDetailLevel(region: BuildingRegion): BuildingDetailLevel {
  return Math.hypot(region.centerX, region.centerZ) <= 0.42 ? "lod2" : "distant";
}

function estimateBuildingVertices(region: BuildingRegion, detailLevel: BuildingDetailLevel): number {
  const footprintVertices = detailLevel === "lod2" ? region.footprint?.length ?? 4 : 4;
  const roofVertices = detailLevel === "lod2" && region.roofType !== "flat" ? footprintVertices + 1 : footprintVertices;
  return footprintVertices * 2 + roofVertices;
}

function validateSceneQuality(heightData: number[], gridSize: number, maxHeight: number, regions: BuildingRegion[]): SceneQualityReport {
  const detailedBuildings = regions.filter((region) => getBuildingDetailLevel(region) === "lod2").length;
  const distantBuildings = regions.length - detailedBuildings;
  const estimatedVertices = gridSize * gridSize + regions.reduce((total, region) => total + estimateBuildingVertices(region, getBuildingDetailLevel(region)), 0);
  return {
    fullGridCoverage: heightData.length === gridSize * gridSize && gridSize >= 128,
    groundedWalls: regions.every((region) => (region.groundHeight ?? 0) >= 0 && (region.wallHeight ?? region.height) >= 0),
    sharpRoofs: regions.every((region) => (region.footprint?.length ?? 0) >= 3 && ["flat", "gabled", "hipped", "dome"].includes(region.roofType) && Number.isFinite(region.roofRise ?? 0) && (region.wallHeight ?? region.height) <= region.height + 0.001),
    continuousTerrain: Number.isFinite(maxHeight) && maxHeight >= 0 && heightData.every((value) => Number.isFinite(value)),
    estimatedVertices,
    withinBrowserBudget: estimatedVertices <= 220_000,
    detailedBuildings,
    distantBuildings,
  };
}

export { getBuildingDetailLevel, validateSceneQuality };
export type { BuildingDetailLevel, SceneQualityReport };
