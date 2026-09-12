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
}

console.log("roof geometry fixtures passed");
