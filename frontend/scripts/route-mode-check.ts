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
const route = await response.json() as { path?: Array<{ row: number; column: number }>; distanceCells?: number };
if (route.distanceCells !== 4 || route.path?.length !== 5) throw new Error("Valid route response was not rendered as a five-cell path.");

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
