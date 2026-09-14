import { Canvas } from "@react-three/fiber";
import { ContactShadows, FlyControls, OrbitControls, PerformanceMonitor, PerspectiveCamera, useTexture } from "@react-three/drei";
import { Suspense, useEffect, useMemo, useState } from "react";
import * as THREE from "three";
import type { BuildingRegion, SceneLayers, SemanticClass } from "../types";
import { createBuildingExtrusionGeometry } from "../buildingGeometry";
import { getBuildingLayout } from "../sceneGeometry";
import { getBuildingDetailLevel, validateSceneQuality } from "../sceneQuality";
import { BUILDING, SEMANTIC_LAYER_DEFINITIONS, createSemanticSurfaceGeometry, getSemanticClassColor, getVisibleSemanticClassIds, prepareSemanticTerrain } from "../semanticTerrain";

type ReconstructionViewerProps = {
  heightData: number[];
  gridSize: number;
  maxHeight: number;
  layers: SceneLayers;
  inputImageUrl: string;
  buildingRegions?: BuildingRegion[];
  semanticData?: number[] | null;
  semanticGridSize?: number | null;
  semanticClasses?: SemanticClass[];
};

type CameraMode = "isometric" | "top" | "fly";

const WORLD_WIDTH = 15;
const WORLD_DEPTH = 11;

function createSurfaceGeometry(heightData: number[], gridSize: number, maxHeight: number, exaggeration: number) {
  const surface = new THREE.PlaneGeometry(WORLD_WIDTH, WORLD_DEPTH, gridSize - 1, gridSize - 1);
  surface.rotateX(-Math.PI / 2);
  const positions = surface.attributes.position;
  const verticalScale = 3.6 / Math.max(maxHeight, 1);

  for (let index = 0; index < positions.count; index += 1) {
    positions.setY(index, (heightData[index] ?? 0) * verticalScale * exaggeration);
  }
  positions.needsUpdate = true;
  surface.computeVertexNormals();
  return surface;
}

function extractBuildingRegions(heightData: number[], gridSize: number, maxHeight: number): BuildingRegion[] {
  const threshold = Math.max(maxHeight * 0.62, 1);
  const mask = heightData.map((height) => height >= threshold);
  const visited = new Uint8Array(mask.length);
  const regions: BuildingRegion[] = [];
  const indexFor = (row: number, column: number) => row * gridSize + column;
  const neighbours = [[-1, 0], [1, 0], [0, -1], [0, 1]] as const;

  for (let row = 0; row < gridSize; row += 1) {
    for (let column = 0; column < gridSize; column += 1) {
      const start = indexFor(row, column);
      if (!mask[start] || visited[start]) continue;

      const queue = [[row, column]];
      const cells: Array<[number, number]> = [];
      visited[start] = 1;
      while (queue.length) {
        const [currentRow, currentColumn] = queue.pop()!;
        cells.push([currentRow, currentColumn]);
        for (const [rowDelta, columnDelta] of neighbours) {
          const nextRow = currentRow + rowDelta;
          const nextColumn = currentColumn + columnDelta;
          if (nextRow < 0 || nextRow >= gridSize || nextColumn < 0 || nextColumn >= gridSize) continue;
          const nextIndex = indexFor(nextRow, nextColumn);
          if (mask[nextIndex] && !visited[nextIndex]) {
            visited[nextIndex] = 1;
            queue.push([nextRow, nextColumn]);
          }
        }
      }

      const minimumArea = 8;
      if (cells.length < minimumArea) continue;
      const rows = cells.map(([cellRow]) => cellRow);
      const columns = cells.map(([, cellColumn]) => cellColumn);
      const minRow = Math.min(...rows);
      const maxRow = Math.max(...rows);
      const minColumn = Math.min(...columns);
      const maxColumn = Math.max(...columns);
      const averageHeight = cells.reduce((total, [cellRow, cellColumn]) => total + heightData[indexFor(cellRow, cellColumn)], 0) / cells.length;
      const centerX = ((minColumn + maxColumn) / 2 / (gridSize - 1) - 0.5);
      const centerZ = ((minRow + maxRow) / 2 / (gridSize - 1) - 0.5);
      regions.push({
        centerX,
        centerZ,
        width: Math.max((maxColumn - minColumn + 1) / gridSize, 0.02),
        depth: Math.max((maxRow - minRow + 1) / gridSize, 0.02),
        height: Math.max(averageHeight, maxHeight * 0.18),
        roofType: "flat",
        source: "browser_fallback",
        footprint: [
          [minColumn / gridSize - 0.5, minRow / gridSize - 0.5],
          [(maxColumn + 1) / gridSize - 0.5, minRow / gridSize - 0.5],
          [(maxColumn + 1) / gridSize - 0.5, (maxRow + 1) / gridSize - 0.5],
          [minColumn / gridSize - 0.5, (maxRow + 1) / gridSize - 0.5],
        ],
        holes: [],
      });
    }
  }
  return regions;
}

function TerrainBase() {
  return <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow position={[0, 0, 0]}><planeGeometry args={[WORLD_WIDTH, WORLD_DEPTH]} /><meshStandardMaterial color="#b6c99e" roughness={1} /></mesh>;
}

function distantBuildingRegion(region: BuildingRegion): BuildingRegion {
  const halfWidth = region.width / 2;
  const halfDepth = region.depth / 2;
  return {
    ...region,
    roofType: "flat",
    roofRise: 0,
    footprint: [[region.centerX - halfWidth, region.centerZ - halfDepth], [region.centerX + halfWidth, region.centerZ - halfDepth], [region.centerX + halfWidth, region.centerZ + halfDepth], [region.centerX - halfWidth, region.centerZ + halfDepth]],
    holes: [],
  };
}

function SemanticTerrain({ terrain, maxHeight, exaggeration, layers, wireframe, semanticClasses }: { terrain: ReturnType<typeof prepareSemanticTerrain>; maxHeight: number; exaggeration: number; layers: SceneLayers; wireframe: boolean; semanticClasses?: SemanticClass[] }) {
  const visibleClassIds = useMemo(() => getVisibleSemanticClassIds({ buildings: layers.buildings, ground: layers.ground, roads: layers.roads, water: layers.water, vegetation: layers.vegetation, trees: layers.trees }), [layers.buildings, layers.ground, layers.roads, layers.trees, layers.vegetation, layers.water]);
  const geometries = useMemo(() => visibleClassIds.map((classId) => ({ classId, geometry: createSemanticSurfaceGeometry(terrain.heights, terrain.classes, terrain.gridSize, classId, maxHeight, exaggeration, terrain.baseHeight) })), [exaggeration, maxHeight, terrain.baseHeight, terrain.classes, terrain.gridSize, terrain.heights, visibleClassIds]);
  useEffect(() => () => geometries.forEach(({ geometry }) => geometry.dispose()), [geometries]);
  return <group>{geometries.map(({ classId, geometry }) => <mesh key={classId} geometry={geometry}>
    <meshBasicMaterial color={getSemanticClassColor(classId, semanticClasses)} wireframe={wireframe} />
  </mesh>)}</group>;
}

function createSlopeGeometry(heightData: number[], gridSize: number, maxHeight: number, exaggeration: number) {
  const geometry = createSurfaceGeometry(heightData, gridSize, maxHeight, exaggeration);
  const colors = new Float32Array(geometry.attributes.position.count * 3);
  const safeMax = Math.max(maxHeight, 1);
  for (let row = 0; row < gridSize; row += 1) {
    for (let column = 0; column < gridSize; column += 1) {
      const index = row * gridSize + column;
      const left = heightData[row * gridSize + Math.max(0, column - 1)] ?? 0;
      const right = heightData[row * gridSize + Math.min(gridSize - 1, column + 1)] ?? 0;
      const up = heightData[Math.max(0, row - 1) * gridSize + column] ?? 0;
      const down = heightData[Math.min(gridSize - 1, row + 1) * gridSize + column] ?? 0;
      const slope = Math.min(1, calculateSlopeDegrees(heightData, gridSize, maxHeight, exaggeration, row, column) / 60);
      const color = new THREE.Color().setHSL(0.58 - slope * 0.58, 0.78, 0.52);
      colors[index * 3] = color.r;
      colors[index * 3 + 1] = color.g;
      colors[index * 3 + 2] = color.b;
    }
  }
  geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  return geometry;
}

function calculateSlopeDegrees(heightData: number[], gridSize: number, maxHeight: number, exaggeration: number, row: number, column: number) {
  const left = heightData[row * gridSize + Math.max(0, column - 1)] ?? 0;
  const right = heightData[row * gridSize + Math.min(gridSize - 1, column + 1)] ?? 0;
  const up = heightData[Math.max(0, row - 1) * gridSize + column] ?? 0;
  const down = heightData[Math.min(gridSize - 1, row + 1) * gridSize + column] ?? 0;
  const verticalScale = 3.6 / Math.max(maxHeight, 1) * exaggeration;
  const horizontalX = WORLD_WIDTH / Math.max(gridSize - 1, 1);
  const horizontalZ = WORLD_DEPTH / Math.max(gridSize - 1, 1);
  return Math.atan(Math.hypot((right - left) * verticalScale / Math.max(horizontalX * 2, 0.001), (down - up) * verticalScale / Math.max(horizontalZ * 2, 0.001))) * 180 / Math.PI;
}

function inspectHeight(heightData: number[], gridSize: number, maxHeight: number, exaggeration: number, point: THREE.Vector3) {
  const column = Math.max(0, Math.min(gridSize - 1, Math.round((point.x / WORLD_WIDTH + 0.5) * (gridSize - 1))));
  const row = Math.max(0, Math.min(gridSize - 1, Math.round((point.z / WORLD_DEPTH + 0.5) * (gridSize - 1))));
  const index = row * gridSize + column;
  const height = heightData[index] ?? 0;
  const slope = calculateSlopeDegrees(heightData, gridSize, maxHeight, exaggeration, row, column);
  return { height, slope };
}

function InspectionPlane({ heightData, gridSize, maxHeight, onInspect }: { heightData: number[]; gridSize: number; maxHeight: number; onInspect: (point: THREE.Vector3) => void }) {
  return <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.02, 0]} onPointerMove={(event) => onInspect(event.point)}>
    <planeGeometry args={[WORLD_WIDTH, WORLD_DEPTH]} />
    <meshBasicMaterial transparent opacity={0} depthWrite={false} />
  </mesh>;
}

function StylizedCity({ heightData, gridSize, maxHeight, exaggeration, buildingRegions, wireframe, semanticData, semanticGridSize, semanticClasses, layers }: Omit<ReconstructionViewerProps, "layers" | "inputImageUrl"> & { exaggeration: number; wireframe: boolean; layers: SceneLayers }) {
  const regions = useMemo(() => buildingRegions?.length ? buildingRegions : extractBuildingRegions(heightData, gridSize, maxHeight), [buildingRegions, gridSize, heightData, maxHeight]);
  const terrain = useMemo(() => prepareSemanticTerrain(heightData, gridSize, maxHeight, semanticData, semanticGridSize, regions), [heightData, gridSize, maxHeight, semanticData, semanticGridSize, regions]);
  const quality = useMemo(() => validateSceneQuality(heightData, gridSize, maxHeight, regions), [heightData, gridSize, maxHeight, regions]);
  const verticalScale = 3.6 / Math.max(maxHeight, 1) * exaggeration;

  return <group userData={{ sceneQuality: quality }}>
    {semanticData?.length ? <SemanticTerrain terrain={terrain} maxHeight={maxHeight} exaggeration={exaggeration} layers={layers} wireframe={wireframe} semanticClasses={semanticClasses} /> : <TerrainBase />}
    {layers.buildings && regions.map((sourceRegion, index) => {
      const detailLevel = getBuildingDetailLevel(sourceRegion);
      const region = detailLevel === "distant" ? distantBuildingRegion(sourceRegion) : sourceRegion;
      const height = region.height * verticalScale;
      const layout = getBuildingLayout(height);
      const width = Math.max(region.width * WORLD_WIDTH, 0.2);
      const depth = Math.max(region.depth * WORLD_DEPTH, 0.2);
      const footprintGeometry = detailLevel === "lod2" ? createBuildingExtrusionGeometry(region, verticalScale, WORLD_WIDTH, WORLD_DEPTH) : null;
      if (footprintGeometry) {
        const materialColor = wireframe ? "#9b94bd" : getSemanticClassColor(BUILDING, semanticClasses);
        const baseY = (region.groundHeight ?? 0) * verticalScale;
        return <group key={`${region.centerX}-${region.centerZ}-${index}`} position={[0, baseY, 0]}>
          <mesh geometry={footprintGeometry} castShadow receiveShadow>
            <meshStandardMaterial color={materialColor} roughness={0.77} wireframe={wireframe} flatShading />
          </mesh>
        </group>;
      }
      return <group key={`${region.centerX}-${region.centerZ}-${index}`} position={[region.centerX * WORLD_WIDTH, 0, region.centerZ * WORLD_DEPTH]}>
        <mesh castShadow receiveShadow position={[0, layout.wallCenterY, 0]}>
          <boxGeometry args={[width, height, depth]} />
          <meshStandardMaterial color={wireframe ? "#9b94bd" : getSemanticClassColor(BUILDING, semanticClasses)} roughness={0.77} wireframe={wireframe} flatShading />
        </mesh>
      </group>;
    })}
  </group>;
}

function HeightSurface({ heightData, gridSize, maxHeight, exaggeration, layers }: ReconstructionViewerProps & { exaggeration: number }) {
  const geometry = useMemo(() => createSurfaceGeometry(heightData, gridSize, maxHeight, exaggeration), [exaggeration, gridSize, heightData, maxHeight]);

  if (!layers.height && !layers.rgb) return null;
  const color = layers.height ? "#8177b6" : "#aeb8c5";
  return <mesh geometry={geometry} castShadow receiveShadow><meshStandardMaterial color={color} roughness={0.82} metalness={0.02} wireframe={layers.wireframe} /></mesh>;
}

function SlopeSurface({ heightData, gridSize, maxHeight, exaggeration, enabled, wireframe }: { heightData: number[]; gridSize: number; maxHeight: number; exaggeration: number; enabled: boolean; wireframe: boolean }) {
  const geometry = useMemo(() => enabled ? createSlopeGeometry(heightData, gridSize, maxHeight, exaggeration) : null, [enabled, exaggeration, gridSize, heightData, maxHeight]);
  if (!geometry) return null;
  return <mesh geometry={geometry} position={[0, 0.012, 0]} receiveShadow><meshStandardMaterial vertexColors polygonOffset polygonOffsetFactor={-1} polygonOffsetUnits={-1} wireframe={wireframe} roughness={0.88} /></mesh>;
}

function RgbSurface({ heightData, gridSize, maxHeight, exaggeration, inputImageUrl }: ReconstructionViewerProps & { exaggeration: number }) {
  const texture = useTexture(inputImageUrl);
  const geometry = useMemo(() => createSurfaceGeometry(heightData, gridSize, maxHeight, exaggeration), [exaggeration, gridSize, heightData, maxHeight]);

  return <mesh geometry={geometry} position={[0, 0.015, 0]}><meshBasicMaterial map={texture} polygonOffset polygonOffsetFactor={-1} polygonOffsetUnits={-1} /></mesh>;
}

function SceneContents({ heightData, gridSize, maxHeight, exaggeration, cameraMode, layers, inputImageUrl, buildingRegions, semanticData, semanticGridSize, semanticClasses, onInspect }: ReconstructionViewerProps & { exaggeration: number; cameraMode: CameraMode; onInspect: (point: THREE.Vector3) => void }) {
  const cameraPosition: [number, number, number] = cameraMode === "isometric" ? [12, 11, 14] : cameraMode === "top" ? [0, 18, 0.01] : [8, 5, 8];

  return (
    <>
      <color attach="background" args={["#f0eff7"]} />
      <ambientLight intensity={1.15} />
      <directionalLight castShadow intensity={2.6} position={[7, 13, 8]} shadow-mapSize={[1024, 1024]} shadow-bias={-0.0002} />
      <directionalLight intensity={0.38} position={[-8, 5, -4]} color="#d7d1ff" />
      {layers.city && <Suspense fallback={null}><StylizedCity heightData={heightData} gridSize={gridSize} maxHeight={maxHeight} exaggeration={exaggeration} buildingRegions={buildingRegions} wireframe={layers.wireframe} semanticData={semanticData} semanticGridSize={semanticGridSize} semanticClasses={semanticClasses} layers={layers} /></Suspense>}
      {layers.city && <ContactShadows position={[0, 0.01, 0]} opacity={0.32} scale={20} blur={1.4} far={5} resolution={256} color="#555064" />}
      <HeightSurface heightData={heightData} gridSize={gridSize} maxHeight={maxHeight} exaggeration={exaggeration} layers={layers} inputImageUrl={inputImageUrl} />
      <SlopeSurface heightData={heightData} gridSize={gridSize} maxHeight={maxHeight} exaggeration={exaggeration} enabled={layers.slope} wireframe={layers.wireframe} />
      {layers.rgb && <Suspense fallback={null}><RgbSurface heightData={heightData} gridSize={gridSize} maxHeight={maxHeight} exaggeration={exaggeration} layers={layers} inputImageUrl={inputImageUrl} /></Suspense>}
      <InspectionPlane heightData={heightData} gridSize={gridSize} maxHeight={maxHeight} onInspect={onInspect} />
      <gridHelper args={[22, 22, "#d5d1e4", "#e5e3ed"]} position={[0, -0.04, 0]} />
      {cameraMode === "fly" ? <FlyControls makeDefault movementSpeed={8} rollSpeed={0.35} dragToLook /> : <OrbitControls makeDefault target={[0, 0.8, 0]} enableDamping dampingFactor={0.08} minDistance={5} maxDistance={28} maxPolarAngle={Math.PI * 0.48} />}
      <PerspectiveCamera makeDefault position={cameraPosition} fov={36} near={0.1} far={100} />
    </>
  );
}

function ReconstructionViewer({ heightData, gridSize, maxHeight, layers, inputImageUrl, buildingRegions, semanticData, semanticGridSize, semanticClasses }: ReconstructionViewerProps) {
  const [cameraMode, setCameraMode] = useState<CameraMode | "fly">("isometric");
  const [exaggeration, setExaggeration] = useState(1);
  const [resetKey, setResetKey] = useState(0);
  const [inspection, setInspection] = useState<{ height: number; slope: number } | null>(null);
  const [renderDpr, setRenderDpr] = useState(1.5);

  return (
    <div className="reconstruction-viewer">
      <Canvas key={`${cameraMode}-${resetKey}`} shadows dpr={[1, renderDpr]} camera={{ position: [12, 11, 14], fov: 36 }}>
        <PerformanceMonitor onDecline={() => setRenderDpr(1)} onIncline={() => setRenderDpr(1.5)} />
        <SceneContents heightData={heightData} gridSize={gridSize} maxHeight={maxHeight} exaggeration={exaggeration} cameraMode={cameraMode} layers={layers} inputImageUrl={inputImageUrl} buildingRegions={buildingRegions} semanticData={semanticData} semanticGridSize={semanticGridSize} semanticClasses={semanticClasses} onInspect={(point) => setInspection(inspectHeight(heightData, gridSize, maxHeight, exaggeration, point))} />
      </Canvas>
      <div className="scene-toolbar" aria-label="Scene controls">
        <button className={cameraMode === "isometric" ? "selected" : ""} onClick={() => setCameraMode("isometric")}>Isometric</button>
        <button className={cameraMode === "top" ? "selected" : ""} onClick={() => setCameraMode("top")}>Top</button>
        <button className={cameraMode === "fly" ? "selected" : ""} onClick={() => setCameraMode("fly")}>Fly</button>
        <button onClick={() => setResetKey((key) => key + 1)}>Reset view</button>
        <label className="exaggeration-control">
          <span>Height {exaggeration.toFixed(1)}×</span>
          <input aria-label="Height exaggeration" type="range" min="1" max="3" step="0.1" value={exaggeration} onChange={(event) => setExaggeration(Number(event.target.value))} />
        </label>
        <span className="scene-quality-label">{inspection ? `Height ${inspection.height.toFixed(1)} m · slope ${inspection.slope.toFixed(1)}°` : `Move over terrain to inspect height and slope · DPR ${renderDpr.toFixed(1)}`}</span>
      </div>
    </div>
  );
}

export { ReconstructionViewer };
