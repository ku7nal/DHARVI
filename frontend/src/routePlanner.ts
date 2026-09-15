import type { EvacuationBrief, PredictionResult, RoutePoint, RouteResult } from "./types";

/** Map a route response cell onto the height scene, even when grids differ. */
function routePointToSceneCell(point: RoutePoint, routeGridSize: number, sceneGridSize: number): RoutePoint {
  return {
    row: Math.max(0, Math.min(sceneGridSize - 1, Math.round(point.row / Math.max(routeGridSize - 1, 1) * Math.max(sceneGridSize - 1, 1)))),
    column: Math.max(0, Math.min(sceneGridSize - 1, Math.round(point.column / Math.max(routeGridSize - 1, 1) * Math.max(sceneGridSize - 1, 1)))),
  };
}

export { routePointToSceneCell };

function expandDebrisZones(zones: RoutePoint[], gridSize: number): RoutePoint[] {
  const cells = new Map<string, RoutePoint>();
  zones.forEach((zone) => {
    for (let row = zone.row - 1; row <= zone.row + 1; row += 1) {
      for (let column = zone.column - 1; column <= zone.column + 1; column += 1) {
        if (row < 0 || row >= gridSize || column < 0 || column >= gridSize) continue;
        cells.set(`${row}:${column}`, { row, column });
      }
    }
  });
  return [...cells.values()];
}

export { expandDebrisZones };

function createEvacuationBrief(route: RouteResult, prediction: PredictionResult): EvacuationBrief {
  const limitations = [
    "Decision support only; verify road status with field teams before dispatch.",
    prediction.heightReference === "relative" ? "Terrain heights are relative estimates, not surveyed elevations." : "Terrain heights are calibrated metric estimates.",
    prediction.semanticSource === "trained" ? "Semantic hazards come from a trained model and may contain classification uncertainty." : "Semantic hazards come from a deterministic fixture mask.",
  ];
  return { briefType: "evacuation-decision-support", generatedAt: new Date().toISOString(), origin: route.start, destination: route.destination, gridSize: route.gridSize, profile: route.profile, distanceCells: route.distanceCells, estimatedTravelTimeMinutes: route.travelTimeMinutes, riskScore: route.riskScore, accessibilityScore: route.accessibilityScore, avoidedHazards: route.avoidedHazards, hazards: route.hazards, prediction: { semanticSource: prediction.semanticSource, boundaryConfidence: prediction.boundaryConfidence ?? null, limitations }, route: route.path };
}

export { createEvacuationBrief };
