const response = await fetch("http://127.0.0.1:8000/api/route", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    semanticData: Array.from({ length: 25 }, (_, index) => index === 12 || index % 5 === 2 ? 5 : 0),
    gridSize: 5,
    start: { row: 0, column: 2 },
    destination: { row: 4, column: 2 },
  }),
});
if (!response.ok) throw new Error(`Expected a valid route, received ${response.status}`);
const route = await response.json() as { path?: Array<{ row: number; column: number }>; distanceCells?: number; hazards?: { blockedRoadCells?: number } };
if (route.distanceCells !== 4 || route.path?.length !== 5) throw new Error("Valid route response was not rendered as a five-cell path.");

for (const profile of ["fastest", "safest", "accessible"]) {
  const profiled = await fetch("http://127.0.0.1:8000/api/route", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ semanticData: Array.from({ length: 25 }, () => 5), gridSize: 5, start: { row: 2, column: 0 }, destination: { row: 2, column: 4 }, profile, heightData: Array.from({ length: 25 }, () => 0) }),
  });
  const profiledRoute = await profiled.json() as { profile?: string; alternatives?: Array<{ travelTimeMinutes?: number; riskScore?: number }> };
  if (!profiled.ok || profiledRoute.profile !== profile || profiledRoute.alternatives?.length !== 3 || profiledRoute.alternatives.some((alternative) => typeof alternative.travelTimeMinutes !== "number" || typeof alternative.riskScore !== "number")) throw new Error(`${profile} route profile did not return ranked metrics.`);
}

const blocked = await fetch("http://127.0.0.1:8000/api/route", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ semanticData: Array.from({ length: 25 }, () => 5), gridSize: 5, start: { row: 2, column: 0 }, destination: { row: 2, column: 4 }, blockedCells: [{ row: 2, column: 2 }] }),
});
if (!blocked.ok) throw new Error(`Expected debris detour to remain routable, received ${blocked.status}`);
const blockedRoute = await blocked.json() as { path?: Array<{ row: number; column: number }>; hazards?: { blockedRoadCells?: number } };
if (blockedRoute.path?.some((point) => point.row === 2 && point.column === 2) || blockedRoute.hazards?.blockedRoadCells !== 1) throw new Error("Debris hazard was not applied to the route.");

const waterLabels = Array.from({ length: 25 }, () => 5);
waterLabels[12] = 4;
const flooded = await fetch("http://127.0.0.1:8000/api/route", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ semanticData: waterLabels, gridSize: 5, start: { row: 2, column: 0 }, destination: { row: 2, column: 4 } }),
});
if (!flooded.ok) throw new Error(`Expected flooded-road rerouting to remain routable, received ${flooded.status}`);
const floodedRoute = await flooded.json() as { path?: Array<{ row: number; column: number }>; hazards?: { waterBlockedRoadCells?: number } };
if (floodedRoute.path?.some((point) => point.row === 2 && point.column === 2) || !(floodedRoute.hazards?.waterBlockedRoadCells ?? 0)) throw new Error("Water hazard was not applied to the route.");

const cleared = await fetch("http://127.0.0.1:8000/api/route", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ semanticData: Array.from({ length: 25 }, () => 5), gridSize: 5, start: { row: 2, column: 0 }, destination: { row: 2, column: 4 }, blockedCells: [] }),
});
const clearedRoute = await cleared.json() as { path?: Array<{ row: number; column: number }> };
if (!cleared.ok || !clearedRoute.path?.some((point) => point.row === 2 && point.column === 2)) throw new Error("Clearing debris did not restore the direct route.");

const invalid = await fetch("http://127.0.0.1:8000/api/route", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ semanticData: Array.from({ length: 9 }, () => 0), gridSize: 3, start: { row: 0, column: 0 }, destination: { row: 2, column: 2 } }),
});
if (invalid.status !== 422) throw new Error(`Expected invalid road points to return 422, received ${invalid.status}`);

const disconnected = await fetch("http://127.0.0.1:8000/api/route", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ semanticData: [5, 0, 0, 0, 0, 0, 0, 0, 5], gridSize: 3, start: { row: 0, column: 0 }, destination: { row: 2, column: 2 } }),
});
if (disconnected.status !== 422) throw new Error(`Expected disconnected roads to return 422, received ${disconnected.status}`);
console.log("route mode API fixture passed");
