import type { RoutePoint } from "../types";

type ElevationReference = "relative" | "absolute";

function clampPinPoint(point: RoutePoint, gridSize: number): RoutePoint {
  const maximum = Math.max(gridSize - 1, 0);
  return {
    row: Math.max(0, Math.min(maximum, Math.round(point.row))),
    column: Math.max(0, Math.min(maximum, Math.round(point.column))),
  };
}

function getPinHeight(point: RoutePoint, heightData: number[], gridSize: number): number {
  return heightData[point.row * gridSize + point.column] ?? 0;
}

function formatElevationReadout(height: number, reference: ElevationReference): string {
  return `${reference === "absolute" ? "Elevation" : "Estimated height"} · ${height.toFixed(1)} m`;
}

export { clampPinPoint, formatElevationReadout, getPinHeight };
export type { ElevationReference };
