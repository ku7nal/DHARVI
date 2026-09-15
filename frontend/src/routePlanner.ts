import type { RoutePoint } from "./types";

/** Map a route response cell onto the height scene, even when grids differ. */
function routePointToSceneCell(point: RoutePoint, routeGridSize: number, sceneGridSize: number): RoutePoint {
  return {
    row: Math.max(0, Math.min(sceneGridSize - 1, Math.round(point.row / Math.max(routeGridSize - 1, 1) * Math.max(sceneGridSize - 1, 1)))),
    column: Math.max(0, Math.min(sceneGridSize - 1, Math.round(point.column / Math.max(routeGridSize - 1, 1) * Math.max(sceneGridSize - 1, 1)))),
  };
}

export { routePointToSceneCell };
