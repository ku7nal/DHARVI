import * as THREE from "three";
import type { BuildingRegion } from "./types";

type RoofPoint = [number, number];

function worldPoints(region: BuildingRegion, worldWidth: number, worldDepth: number): RoofPoint[] {
  return (region.footprint ?? []).map(([x, z]) => [x * worldWidth, z * worldDepth]);
}

function bounds(points: RoofPoint[]) {
  return points.reduce((result, [x, z]) => ({
    minX: Math.min(result.minX, x),
    maxX: Math.max(result.maxX, x),
    minZ: Math.min(result.minZ, z),
    maxZ: Math.max(result.maxZ, z),
  }), { minX: Infinity, maxX: -Infinity, minZ: Infinity, maxZ: -Infinity });
}

function polygonGeometry(points: RoofPoint[], rise: number, roofType: BuildingRegion["roofType"]): THREE.BufferGeometry {
  const roofBounds = bounds(points);
  const centerX = (roofBounds.minX + roofBounds.maxX) / 2;
  const centerZ = (roofBounds.minZ + roofBounds.maxZ) / 2;
  const width = Math.max(roofBounds.maxX - roofBounds.minX, 0.001);
  const depth = Math.max(roofBounds.maxZ - roofBounds.minZ, 0.001);
  const vertices: number[] = [];
  const append = (x: number, z: number, y: number) => vertices.push(x, y, z);

  if (roofType === "gabled" && points.length === 4) {
    const corners = [
      [roofBounds.minX, roofBounds.minZ], [roofBounds.maxX, roofBounds.minZ],
      [roofBounds.maxX, roofBounds.maxZ], [roofBounds.minX, roofBounds.maxZ],
    ] as RoofPoint[];
    corners.forEach(([x, z]) => append(x, 0, z));
    if (width >= depth) {
      append(centerX, 0, roofBounds.minZ);
      append(centerX, rise, roofBounds.maxZ);
    } else {
      append(roofBounds.minX, 0, centerZ);
      append(roofBounds.maxX, rise, centerZ);
    }
    const indices = width >= depth
      ? [0, 1, 4, 1, 2, 5, 2, 3, 5, 3, 0, 4]
      : [0, 1, 5, 1, 2, 4, 2, 3, 4, 3, 0, 5];
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
    geometry.setIndex(indices);
    geometry.computeVertexNormals();
    return geometry;
  }

  points.forEach(([x, z]) => {
    const normalizedX = Math.abs((x - centerX) / (width / 2));
    const normalizedZ = Math.abs((z - centerZ) / (depth / 2));
    const edgeDistance = roofType === "hipped" ? Math.max(normalizedX, normalizedZ) : Math.sqrt(normalizedX ** 2 + normalizedZ ** 2);
    const pointHeight = roofType === "hipped" ? Math.max(0, rise * (1 - edgeDistance)) : Math.max(0, rise * (1 - Math.min(edgeDistance, 1)));
    append(x, pointHeight, z);
  });
  const centerIndex = points.length;
  append(centerX, rise, centerZ);
  const indices: number[] = [];
  for (let index = 0; index < points.length; index += 1) {
    indices.push(index, (index + 1) % points.length, centerIndex);
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}

function createRoofGeometry(region: BuildingRegion, verticalScale: number, worldWidth: number, worldDepth: number): THREE.BufferGeometry | null {
  const points = worldPoints(region, worldWidth, worldDepth);
  if (points.length < 3) return null;
  const rise = Math.max((region.roofRise ?? 0) * verticalScale, 0.02);
  if (region.roofType === "flat") {
    const shape = new THREE.Shape(points.map(([x, z]) => new THREE.Vector2(x, -z)));
    for (const hole of region.holes ?? []) {
      if (hole.length >= 3) shape.holes.push(new THREE.Path(hole.map(([x, z]) => new THREE.Vector2(x * worldWidth, -z * worldDepth))));
    }
    const geometry = new THREE.ShapeGeometry(shape);
    geometry.rotateX(-Math.PI / 2);
    geometry.computeVertexNormals();
    return geometry;
  }
  return polygonGeometry(points, rise, region.roofType);
}

export { createRoofGeometry };
