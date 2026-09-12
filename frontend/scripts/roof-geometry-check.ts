import { createRoofGeometry } from "../src/roofGeometry.ts";
import type { BuildingRegion } from "../src/types.ts";

const footprint: Array<[number, number]> = [[-0.2, -0.15], [0.2, -0.15], [0.2, 0.15], [-0.2, 0.15]];
const regions: BuildingRegion[] = [
  { centerX: 0, centerZ: 0, width: 0.4, depth: 0.3, height: 2, roofType: "flat", source: "test", footprint },
  { centerX: 0, centerZ: 0, width: 0.4, depth: 0.3, height: 2, roofType: "gabled", source: "test", footprint, roofRise: 0.5 },
  { centerX: 0, centerZ: 0, width: 0.4, depth: 0.3, height: 2, roofType: "hipped", source: "test", footprint, roofRise: 0.5 },
  { centerX: 0, centerZ: 0, width: 0.4, depth: 0.3, height: 2, roofType: "dome", source: "test", footprint: [[-0.2, -0.15], [0.1, -0.15], [0.2, 0], [0.1, 0.15], [-0.2, 0.15]], roofRise: 0.5 },
];

for (const region of regions) {
  const geometry = createRoofGeometry(region, 1, 15, 11);
  if (!geometry || !geometry.getAttribute("position") || !geometry.getIndex()) {
    throw new Error(`${region.roofType} roof did not produce indexed geometry`);
  }
  if (!geometry.getAttribute("normal")) throw new Error(`${region.roofType} roof is missing normals`);
  if (region.roofType !== "flat" && !geometry.getAttribute("uv")) throw new Error(`${region.roofType} roof is missing planar UVs`);
  const edgeHeights = Array.from({ length: region.footprint?.length ?? 0 }, (_, index) => geometry.getAttribute("position").getY(index));
  if (region.roofType !== "flat" && edgeHeights.some((height) => Math.abs(height) > 0.0001)) {
    throw new Error(`${region.roofType} roof does not share its eave edge with the wall`);
  }
}

const gabled = createRoofGeometry(regions[1], 1, 15, 11)!;
const gabledHeights = Array.from({ length: 6 }, (_, index) => gabled.getAttribute("position").getY(index));
if (gabledHeights[4] !== gabledHeights[5] || gabledHeights[4] <= 0) throw new Error("gabled ridge is not level");

console.log("roof geometry fixtures passed");
