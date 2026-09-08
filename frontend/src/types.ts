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
};

type SceneLayers = {
  city: boolean;
  height: boolean;
  rgb: boolean;
  wireframe: boolean;
};

export type { PredictionResult, SceneLayers };
