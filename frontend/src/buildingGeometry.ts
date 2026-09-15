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

function createFootprintShape(region: BuildingRegion, worldWidth: number, worldDepth: number): THREE.Shape | null {
  if (!region.footprint || region.footprint.length < 3) return null;
  const shape = new THREE.Shape(region.footprint.map(([x, z]) => new THREE.Vector2(x * worldWidth, -z * worldDepth)));
  for (const hole of region.holes ?? []) {
    if (hole.length >= 3) shape.holes.push(new THREE.Path(hole.map(([x, z]) => new THREE.Vector2(x * worldWidth, -z * worldDepth))));
  }
  return shape;
}

function isConvexFootprint(footprint: Array<[number, number]>): boolean {
  let winding = 0;
  for (let index = 0; index < footprint.length; index += 1) {
    const current = footprint[index];
    const next = footprint[(index + 1) % footprint.length];
    const afterNext = footprint[(index + 2) % footprint.length];
    const cross = (next[0] - current[0]) * (afterNext[1] - next[1]) - (next[1] - current[1]) * (afterNext[0] - next[0]);
    if (Math.abs(cross) < 1e-8) continue;
    if (!winding) winding = Math.sign(cross);
    else if (Math.sign(cross) !== winding) return false;
  }
  return winding !== 0;
}

function createRoofGeometry(region: BuildingRegion, verticalScale: number, worldWidth: number, worldDepth: number): THREE.BufferGeometry | null {
  if (!region.footprint || region.footprint.length < 3 || region.roofType === "flat" || !isConvexFootprint(region.footprint)) return null;
  const outline = region.footprint.map(([x, z]) => new THREE.Vector3(x * worldWidth, 0, -z * worldDepth));
  const box = new THREE.Box3().setFromPoints(outline);
  const centerX = (box.min.x + box.max.x) / 2;
  const centerZ = (box.min.z + box.max.z) / 2;
  const rise = Math.max(region.roofRise ?? 0, region.roofType === "stepped" ? 0.12 : 0.04) * verticalScale;
  const wallHeight = Math.max(region.wallHeight ?? region.height, 0) * verticalScale;

  const vertices: number[] = [];
  for (const point of outline) {
    vertices.push(point.x, wallHeight, point.z);
  }
  if (region.roofType === "stepped") {
    for (const point of outline) {
      vertices.push(centerX + (point.x - centerX) * 0.68, wallHeight + rise * 0.48, centerZ + (point.z - centerZ) * 0.68);
    }
    vertices.push(centerX, wallHeight + rise, centerZ);
  } else {
    vertices.push(centerX, wallHeight + rise, centerZ);
  }
  const indices: number[] = [];
  if (region.roofType === "stepped") {
    const innerOffset = outline.length;
    const centerIndex = outline.length * 2;
    for (let index = 0; index < outline.length; index += 1) {
      const next = (index + 1) % outline.length;
      indices.push(index, next, innerOffset + next, index, innerOffset + next, innerOffset + index);
      indices.push(centerIndex, innerOffset + index, innerOffset + next);
    }
  } else {
    const centerIndex = outline.length;
    for (let index = 0; index < outline.length; index += 1) {
      const next = (index + 1) % outline.length;
      indices.push(centerIndex, index, next);
    }
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}

export { createBuildingExtrusionGeometry, createRoofGeometry };
