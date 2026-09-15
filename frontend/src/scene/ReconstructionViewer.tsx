import { Canvas } from "@react-three/fiber";
import { ContactShadows, FlyControls, OrbitControls, OrthographicCamera, PerformanceMonitor, PerspectiveCamera, useTexture } from "@react-three/drei";
import { Suspense, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import type { BuildingRegion, SceneLayers, SemanticClass } from "../types";
import { createBuildingExtrusionGeometry, createRoofGeometry } from "../buildingGeometry";
import { getBuildingLayout } from "../sceneGeometry";
import { MAX_TREE_INSTANCES, getBuildingDetailLevel, validateSceneQuality } from "../sceneQuality";
import { BUILDING, SEMANTIC_LAYER_DEFINITIONS, TREE, createSemanticSurfaceGeometry, getSemanticClassColor, getVisibleSemanticClassIds, prepareSemanticTerrain } from "../semanticTerrain";

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

const BUILDING_MATERIAL_VARIANTS = ["#c7cbd1", "#c4c9d2", "#cbd0d5", "#bfc6d0", "#d0d1d0"];

function getBuildingMaterialColor(region: BuildingRegion, index: number, semanticClasses?: SemanticClass[]): string {
  const semanticColor = getSemanticClassColor(BUILDING, semanticClasses);
  const seed = Math.abs(Math.round((region.centerX * 97 + region.centerZ * 53) * 1000)) + index;
  if (semanticColor === "#c7cbd1") return BUILDING_MATERIAL_VARIANTS[seed % BUILDING_MATERIAL_VARIANTS.length];
  return new THREE.Color(semanticColor).offsetHSL(0, 0, ((seed % 5) - 2) * 0.025).getHexString().replace(/^/, "#");
}

function getRoofType(region: BuildingRegion): BuildingRegion["roofType"] {
  if (region.roofType !== "flat") return region.roofType;
  const area = region.width * region.depth;
  return getBuildingDetailLevel(region) === "lod2" && area > 0.045 ? "stepped" : "flat";
}

type TreePoint = { x: number; y: number; z: number; scale: number };

function getTreePoints(terrain: ReturnType<typeof prepareSemanticTerrain>, maxHeight: number, exaggeration: number): TreePoint[] {
  const treeCells = terrain.classes.reduce((count, classId) => count + (classId === TREE ? 1 : 0), 0);
  if (!treeCells) return [];
  const stride = Math.max(1, Math.ceil(Math.sqrt(treeCells / MAX_TREE_INSTANCES)));
  const verticalScale = 3.6 / Math.max(maxHeight, 1) * exaggeration;
  const points: TreePoint[] = [];
  for (let row = 0; row < terrain.gridSize; row += stride) {
    for (let column = 0; column < terrain.gridSize; column += stride) {
      const index = row * terrain.gridSize + column;
      if (terrain.classes[index] !== TREE) continue;
      const jitter = ((row * 17 + column * 31) % 9 - 4) / 12;
      points.push({
        x: ((column + 0.5 + jitter) / terrain.gridSize - 0.5) * WORLD_WIDTH,
        y: (terrain.heights[index] ?? terrain.baseHeight) * verticalScale + 0.03,
        z: ((row + 0.5 - jitter) / terrain.gridSize - 0.5) * WORLD_DEPTH,
        scale: 0.84 + ((row * 13 + column * 7) % 5) * 0.08,
      });
      if (points.length >= MAX_TREE_INSTANCES) return points;
    }
  }
  return points;
}

function TreeInstances({ terrain, maxHeight, exaggeration, visible }: { terrain: ReturnType<typeof prepareSemanticTerrain>; maxHeight: number; exaggeration: number; visible: boolean }) {
  const points = useMemo(() => getTreePoints(terrain, maxHeight, exaggeration), [exaggeration, maxHeight, terrain]);
  const trunkRef = useRef<THREE.InstancedMesh>(null);
  const canopyRef = useRef<THREE.InstancedMesh>(null);
  useLayoutEffect(() => {
    const trunk = trunkRef.current;
    const canopy = canopyRef.current;
    if (!trunk || !canopy) return;
    const matrix = new THREE.Matrix4();
    for (let index = 0; index < points.length; index += 1) {
      const point = points[index];
      matrix.makeScale(point.scale, point.scale, point.scale);
      matrix.setPosition(point.x, point.y + 0.16 * point.scale, point.z);
      trunk.setMatrixAt(index, matrix);
      matrix.makeScale(point.scale, point.scale, point.scale);
      matrix.setPosition(point.x, point.y + 0.48 * point.scale, point.z);
      canopy.setMatrixAt(index, matrix);
    }
    trunk.instanceMatrix.needsUpdate = true;
    canopy.instanceMatrix.needsUpdate = true;
  }, [points]);
  if (!visible || !points.length) return null;
  return <group userData={{ instanceCount: points.length }}>
    <instancedMesh ref={trunkRef} args={[undefined, undefined, points.length]} castShadow>
      <cylinderGeometry args={[0.045, 0.06, 0.32, 6]} />
      <meshStandardMaterial color="#705844" roughness={0.95} />
    </instancedMesh>
    <instancedMesh ref={canopyRef} args={[undefined, undefined, points.length]} castShadow>
      <coneGeometry args={[0.28, 0.56, 7]} />
      <meshStandardMaterial color="#477653" roughness={0.9} flatShading />
    </instancedMesh>
  </group>;
}

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
    <TreeInstances terrain={terrain} maxHeight={maxHeight} exaggeration={exaggeration} visible={layers.trees && Boolean(semanticData?.length)} />
    {layers.buildings && regions.map((sourceRegion, index) => {
      const region = sourceRegion;
      const height = region.height * verticalScale;
      const layout = getBuildingLayout(height);
      const width = Math.max(region.width * WORLD_WIDTH, 0.2);
      const depth = Math.max(region.depth * WORLD_DEPTH, 0.2);
      const footprintGeometry = createBuildingExtrusionGeometry(region, verticalScale, WORLD_WIDTH, WORLD_DEPTH);
      if (footprintGeometry) {
        const roofRegion = { ...region, roofType: getRoofType(region) };
        const roofGeometry = createRoofGeometry(roofRegion, verticalScale, WORLD_WIDTH, WORLD_DEPTH);
        const materialColor = wireframe ? "#9b94bd" : getBuildingMaterialColor(region, index, semanticClasses);
        const roofColor = wireframe ? "#9b94bd" : new THREE.Color(materialColor).offsetHSL(0, -0.02, -0.08).getHexString().replace(/^/, "#");
        const baseY = (region.groundHeight ?? 0) * verticalScale;
        return <group key={`${region.centerX}-${region.centerZ}-${index}`} position={[0, baseY, 0]}>
          <mesh geometry={footprintGeometry} castShadow receiveShadow>
            <meshStandardMaterial color={materialColor} roughness={0.77} wireframe={wireframe} flatShading />
          </mesh>
          {roofGeometry && <mesh geometry={roofGeometry} castShadow receiveShadow>
            <meshStandardMaterial color={roofColor} roughness={0.88} wireframe={wireframe} flatShading />
          </mesh>}
        </group>;
      }
      return <group key={`${region.centerX}-${region.centerZ}-${index}`} position={[region.centerX * WORLD_WIDTH, 0, region.centerZ * WORLD_DEPTH]}>
        <mesh castShadow receiveShadow position={[0, layout.wallCenterY, 0]}>
          <boxGeometry args={[width, height, depth]} />
          <meshStandardMaterial color={wireframe ? "#9b94bd" : getBuildingMaterialColor(region, index, semanticClasses)} roughness={0.77} wireframe={wireframe} flatShading />
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

function SceneContents({ heightData, gridSize, maxHeight, exaggeration, cameraMode, presentationMode, layers, inputImageUrl, buildingRegions, semanticData, semanticGridSize, semanticClasses, onInspect }: ReconstructionViewerProps & { exaggeration: number; cameraMode: CameraMode; presentationMode: boolean; onInspect: (point: THREE.Vector3) => void }) {
  const cameraPosition: [number, number, number] = cameraMode === "isometric" ? [12, 11, 14] : cameraMode === "top" ? [0, 18, 0.01] : [8, 5, 8];

  return (
    <>
      <color attach="background" args={["#f0eff7"]} />
      <ambientLight intensity={0.92} />
      <hemisphereLight intensity={0.42} color="#fff8ed" groundColor="#8998b4" />
      <directionalLight castShadow intensity={3.1} position={[7, 13, 8]} shadow-mapSize={[1024, 1024]} shadow-bias={-0.0002} shadow-camera-near={0.1} shadow-camera-far={40} />
      <directionalLight intensity={0.48} position={[-8, 5, -4]} color="#d7d1ff" />
      {layers.city && <Suspense fallback={null}><StylizedCity heightData={heightData} gridSize={gridSize} maxHeight={maxHeight} exaggeration={exaggeration} buildingRegions={buildingRegions} wireframe={layers.wireframe} semanticData={semanticData} semanticGridSize={semanticGridSize} semanticClasses={semanticClasses} layers={layers} /></Suspense>}
      {layers.city && <ContactShadows position={[0, 0.01, 0]} opacity={0.38} scale={20} blur={1.6} far={8} resolution={256} color="#555064" />}
      <HeightSurface heightData={heightData} gridSize={gridSize} maxHeight={maxHeight} exaggeration={exaggeration} layers={layers} inputImageUrl={inputImageUrl} />
      <SlopeSurface heightData={heightData} gridSize={gridSize} maxHeight={maxHeight} exaggeration={exaggeration} enabled={layers.slope} wireframe={layers.wireframe} />
      {layers.rgb && <Suspense fallback={null}><RgbSurface heightData={heightData} gridSize={gridSize} maxHeight={maxHeight} exaggeration={exaggeration} layers={layers} inputImageUrl={inputImageUrl} /></Suspense>}
      {!presentationMode && <InspectionPlane heightData={heightData} gridSize={gridSize} maxHeight={maxHeight} onInspect={onInspect} />}
      {!presentationMode && <gridHelper args={[22, 22, "#d5d1e4", "#e5e3ed"]} position={[0, -0.04, 0]} />}
      {cameraMode === "fly" ? <FlyControls makeDefault movementSpeed={8} rollSpeed={0.35} dragToLook /> : <OrbitControls makeDefault target={[0, 0.8, 0]} enableDamping dampingFactor={0.08} minDistance={5} maxDistance={28} maxPolarAngle={Math.PI * 0.48} />}
      {presentationMode ? <OrthographicCamera makeDefault position={cameraPosition} zoom={30} near={0.1} far={100} onUpdate={(camera) => camera.lookAt(0, 0.8, 0)} /> : <PerspectiveCamera makeDefault position={cameraPosition} fov={36} near={0.1} far={100} />}
    </>
  );
}

function SceneControlIcon({ name }: { name: "search" | "plus" | "minus" | "focus" | "top" | "image" }) {
  const paths = {
    search: <><circle cx="10.5" cy="10.5" r="6.5" /><path d="m15.5 15.5 4.25 4.25" /></>,
    plus: <><path d="M12 5v14M5 12h14" /></>,
    minus: <path d="M5 12h14" />,
    focus: <><path d="M8 3H5a2 2 0 0 0-2 2v3M16 3h3a2 2 0 0 1 2 2v3M21 16v3a2 2 0 0 1-2 2h-3M8 21H5a2 2 0 0 1-2-2v-3" /><rect x="8" y="8" width="8" height="8" rx="1" /></>,
    top: <><path d="m12 3 8 4-8 4-8-4 8-4Z" /><path d="m4 12 8 4 8-4M4 17l8 4 8-4" /></>,
    image: <><rect x="3" y="4" width="18" height="16" rx="2" /><circle cx="8" cy="9" r="1.4" /><path d="m4 17 4.5-4.5 3 3 2.25-2.25L20 19" /></>,
  };

  return <svg aria-hidden="true" className="scene-control-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>;
}

function ReconstructionViewer({ heightData, gridSize, maxHeight, layers, inputImageUrl, buildingRegions, semanticData, semanticGridSize, semanticClasses }: ReconstructionViewerProps) {
  const [cameraMode, setCameraMode] = useState<CameraMode | "fly">("isometric");
  const [exaggeration, setExaggeration] = useState(1);
  const [resetKey, setResetKey] = useState(0);
  const [inspection, setInspection] = useState<{ height: number; slope: number } | null>(null);
  const [renderDpr, setRenderDpr] = useState(1.5);
  const [presentationMode, setPresentationMode] = useState(true);
  const [showSourceImage, setShowSourceImage] = useState(layers.rgb);

  void inspection;

  return (
    <div className="reconstruction-viewer">
      <Canvas key={`${cameraMode}-${presentationMode}-${resetKey}`} shadows dpr={[1, renderDpr]} gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.08 }} camera={{ position: [12, 11, 14], fov: 36 }}>
        <PerformanceMonitor onDecline={() => setRenderDpr(1)} onIncline={() => setRenderDpr(1.5)} />
        <SceneContents heightData={heightData} gridSize={gridSize} maxHeight={maxHeight} exaggeration={exaggeration} cameraMode={cameraMode} presentationMode={presentationMode} layers={{ ...layers, rgb: showSourceImage }} inputImageUrl={inputImageUrl} buildingRegions={buildingRegions} semanticData={semanticData} semanticGridSize={semanticGridSize} semanticClasses={semanticClasses} onInspect={(point) => setInspection(inspectHeight(heightData, gridSize, maxHeight, exaggeration, point))} />
      </Canvas>
      <div className="scene-controls" aria-label="Scene controls">
        <button className="scene-control-button" aria-label="Reset view" title="Reset view" onClick={() => setResetKey((key) => key + 1)}><SceneControlIcon name="search" /></button>
        <div className="scene-control-group" aria-label="Height controls">
          <button className="scene-control-button" aria-label="Increase height" title="Increase height" onClick={() => setExaggeration((value) => Math.min(3, Number((value + 0.1).toFixed(1))))}><SceneControlIcon name="plus" /></button>
          <button className="scene-control-button" aria-label="Decrease height" title="Decrease height" onClick={() => setExaggeration((value) => Math.max(1, Number((value - 0.1).toFixed(1))))}><SceneControlIcon name="minus" /></button>
        </div>
        <button className={`scene-control-button ${cameraMode === "top" ? "selected" : ""}`} aria-label="Top view" title="Top view" aria-pressed={cameraMode === "top"} onClick={() => setCameraMode("top")}><SceneControlIcon name="top" /></button>
        <button className={`scene-control-button ${presentationMode ? "selected" : ""}`} aria-label="Toggle presentation view" title={presentationMode ? "Debug view" : "Presentation view"} aria-pressed={presentationMode} onClick={() => setPresentationMode((value) => !value)}><SceneControlIcon name="focus" /></button>
        <button className={`scene-control-button ${showSourceImage ? "selected" : ""}`} aria-label="Toggle source image" title="Toggle source image" aria-pressed={showSourceImage} onClick={() => setShowSourceImage((value) => !value)}><SceneControlIcon name="image" /></button>
      </div>
    </div>
  );
}

export { ReconstructionViewer };
