type PredictionResult = {
  id: string;
  status: "complete";
  inputImageUrl: string;
  heightMapUrl: string;
  width: number;
  height: number;
  predictionWidth: number;
  predictionHeight: number;
  minHeight: number;
  maxHeight: number;
  resultType: "estimated_ndsm";
  heightUnit: "meters";
  sourceName: string;
  isFixture: boolean;
  gridSize: number;
  heightData: number[];
  semanticClasses?: SemanticClass[];
  semanticGridSize?: number | null;
  semanticData?: number[] | null;
  semanticMapUrl?: string | null;
  semanticSource?: "fixture" | "trained" | "unavailable";
  buildingRegions?: BuildingRegion[];
  buildingRegionSource?: "height_threshold_fallback" | "semantic_head";
  inputFormat: "image" | "geotiff" | "example";
  geospatial: GeoSpatialMetadata | null;
};

type BuildingRegion = {
  centerX: number;
  centerZ: number;
  width: number;
  depth: number;
  height: number;
  roofType: "flat" | "gabled" | "hipped" | "dome";
  source: string;
  footprint?: Array<[number, number]>;
  holes?: Array<Array<[number, number]>>;
  groundHeight?: number;
  roofHeight?: number;
  wallHeight?: number;
  roofRise?: number;
};

type SemanticClass = {
  id: number;
  name: "others" | "ground" | "low_vegetation" | "building" | "water" | "road" | "tree";
  label: string;
  color: string;
};

type GeoSpatialMetadata = {
  crs: string | null;
  bounds: { left: number; bottom: number; right: number; top: number };
  transform: number[];
  resolution: [number, number];
  bands: number;
  driver: string;
  validPixelFraction?: number;
};

type SceneLayers = {
  city: boolean;
  buildings: boolean;
  ground: boolean;
  roads: boolean;
  water: boolean;
  vegetation: boolean;
  trees: boolean;
  height: boolean;
  rgb: boolean;
  wireframe: boolean;
};

const DEFAULT_SCENE_LAYERS: SceneLayers = { city: true, buildings: true, ground: true, roads: true, water: true, vegetation: true, trees: true, height: false, rgb: false, wireframe: false };

type BenchmarkResult = {
  id: string;
  name: string;
  sourceDataset: string;
  split: string;
  referenceStatus: "scaffold_fixture" | "validated";
  inputImageUrl: string;
  groundTruthUrl: string;
  predictionUrl: string;
  errorMapUrl: string;
  metrics: { rmse: number; mae: number; correlation: number };
  comparison?: {
    baseline: { rmse: number; mae: number; correlation: number; buildingBoundaryF1: number };
    improved: { rmse: number; mae: number; correlation: number; buildingBoundaryF1: number };
  };
  width: number;
  height: number;
};

export { DEFAULT_SCENE_LAYERS };
export type { BenchmarkResult, BuildingRegion, GeoSpatialMetadata, PredictionResult, SceneLayers, SemanticClass };
