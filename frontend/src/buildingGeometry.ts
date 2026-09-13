import * as THREE from "three";
import type { BuildingRegion } from "./types";

function createBuildingExtrusionGeometry(region: BuildingRegion, verticalScale: number, worldWidth: number, worldDepth: number): THREE.ExtrudeGeometry | null {
  if (!region.footprint || region.footprint.length < 3) return null;
  const shape = new THREE.Shape(region.footprint.map(([x, z]) => new THREE.Vector2(x * worldWidth, -z * worldDepth)));
  for (const hole of region.holes ?? []) {
    if (hole.length >= 3) {
      shape.holes.push(new THREE.Path(hole.map(([x, z]) => new THREE.Vector2(x * worldWidth, -z * worldDepth))));
    }
  }
  const geometry = new THREE.ExtrudeGeometry(shape, {
    bevelEnabled: false,
    curveSegments: 1,
    depth: Math.max((region.wallHeight ?? region.height) * verticalScale, 0.05),
  });
  geometry.rotateX(-Math.PI / 2);
  return geometry;
}

export { createBuildingExtrusionGeometry };
