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
  inputFormat: "image" | "geotiff" | "example";
  geospatial: GeoSpatialMetadata | null;
};

type GeoSpatialMetadata = {
  crs: string | null;
  bounds: { left: number; bottom: number; right: number; top: number };
  transform: number[];
  resolution: [number, number];
  bands: number;
  driver: string;
};

type SceneLayers = {
  city: boolean;
  height: boolean;
  rgb: boolean;
  wireframe: boolean;
};

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
  width: number;
  height: number;
};

export type { BenchmarkResult, GeoSpatialMetadata, PredictionResult, SceneLayers };
