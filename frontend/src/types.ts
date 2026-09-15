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
  resultType: "estimated_ndsm" | "metric_dsm";
  heightReference: "relative" | "absolute";
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
  boundaryMapUrl?: string | null;
  boundaryGridSize?: number | null;
  boundaryData?: number[] | null;
  boundarySource?: "trained" | "unavailable";
  boundaryConfidence?: number | null;
  buildingRegions?: BuildingRegion[];
  buildingRegionSource?: "height_threshold_fallback" | "semantic_head";
  inputFormat: "image" | "geotiff" | "example";
  geospatial: GeoSpatialMetadata | null;
  dsmUrl?: string | null;
  calibration?: CalibrationMetadata;
};

type CalibrationMetadata = {
  status: "not_applicable" | "calibrated" | "insufficient_ground_evidence" | "invalid_ground_control_points" | "missing_spatial_reference" | "invalid_spatial_metadata";
  method: string | null;
  confidence: number | null;
  residualError: number | null;
  groundPixelCount: number | null;
  error?: string;
};

type BuildingRegion = {
  centerX: number;
  centerZ: number;
  width: number;
  depth: number;
  height: number;
  roofType: "flat" | "stepped" | "gabled" | "hipped" | "dome";
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
  slope: boolean;
  rgb: boolean;
  wireframe: boolean;
};

type RoutePoint = { row: number; column: number };
type RoutePoints = { start?: RoutePoint; destination?: RoutePoint };

type RouteResult = {
  path: RoutePoint[];
  start: RoutePoint;
  destination: RoutePoint;
  gridSize: number;
  distanceCells: number;
  hazards: RouteHazards;
  profile: RouteProfile;
  selectedIndex: number;
  travelTimeMinutes: number;
  riskScore: number;
  accessibilityScore: number;
  avoidedHazards: string[];
  profileScore: number;
  alternatives: RouteAlternative[];
};

type RouteProfile = "fastest" | "safest" | "accessible";
type RouteAlternative = {
  path: RoutePoint[];
  distanceCells: number;
  travelTimeMinutes: number;
  riskScore: number;
  accessibilityScore: number;
  avoidedHazards: string[];
  profileScore: number;
};

type RouteHazards = {
  waterCells: number;
  debrisCells: number;
  blockedRoadCells: number;
  waterBlockedRoadCells: number;
  waterAvoidance: boolean;
};

const DEFAULT_SCENE_LAYERS: SceneLayers = { city: true, buildings: true, ground: true, roads: true, water: true, vegetation: true, trees: true, height: false, slope: false, rgb: false, wireframe: false };

type BenchmarkResult = {
  id: string;
  name: string;
  sourceDataset: string;
  split: string;
  referenceStatus: "scaffold_fixture" | "validated";
  heightReference: "relative" | "metric";
  landscapeGroup: "urban" | "sparse" | "hilly" | "forested";
  coverageNote: string;
  knownLimitations: string[];
  inputImageUrl: string;
  groundTruthUrl: string;
  predictionUrl: string;
  errorMapUrl: string;
  metrics: { rmse: number; mae: number; correlation: number; semanticMiou: number; buildingIoU: number; buildingBoundaryF1: number };
  comparison?: {
    baseline: BenchmarkResult["metrics"];
    improved: BenchmarkResult["metrics"];
  };
  width: number;
  height: number;
};

export { DEFAULT_SCENE_LAYERS };
export type { BenchmarkResult, BuildingRegion, CalibrationMetadata, GeoSpatialMetadata, PredictionResult, RouteAlternative, RouteHazards, RoutePoint, RoutePoints, RouteProfile, RouteResult, SceneLayers, SemanticClass };
