import { Canvas } from "@react-three/fiber";
import { OrbitControls, PerspectiveCamera, useTexture } from "@react-three/drei";
import { Suspense, useMemo, useState } from "react";
import * as THREE from "three";
import type { SceneLayers } from "../types";

type ReconstructionViewerProps = {
  heightData: number[];
  gridSize: number;
  maxHeight: number;
  layers: SceneLayers;
  inputImageUrl: string;
};

type CameraMode = "isometric" | "top";

const WORLD_WIDTH = 15;
const WORLD_DEPTH = 11;

type BuildingRegion = {
  centerX: number;
  centerZ: number;
  width: number;
  depth: number;
  height: number;
};

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
      const maximumArea = gridSize * gridSize * 0.16;
      if (cells.length < minimumArea || cells.length > maximumArea) continue;
      const rows = cells.map(([cellRow]) => cellRow);
      const columns = cells.map(([, cellColumn]) => cellColumn);
      const minRow = Math.min(...rows);
      const maxRow = Math.max(...rows);
      const minColumn = Math.min(...columns);
      const maxColumn = Math.max(...columns);
      const averageHeight = cells.reduce((total, [cellRow, cellColumn]) => total + heightData[indexFor(cellRow, cellColumn)], 0) / cells.length;
      const centerX = ((minColumn + maxColumn) / 2 / (gridSize - 1) - 0.5) * WORLD_WIDTH;
      const centerZ = ((minRow + maxRow) / 2 / (gridSize - 1) - 0.5) * WORLD_DEPTH;
      regions.push({
        centerX,
        centerZ,
        width: Math.max((maxColumn - minColumn + 1) / gridSize * WORLD_WIDTH, 0.22),
        depth: Math.max((maxRow - minRow + 1) / gridSize * WORLD_DEPTH, 0.22),
        height: Math.max(averageHeight, maxHeight * 0.18),
      });
    }
  }
  return regions;
}

function TerrainBase() {
  return <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow position={[0, -0.03, 0]}><planeGeometry args={[WORLD_WIDTH, WORLD_DEPTH]} /><meshStandardMaterial color="#b6c99e" roughness={1} /></mesh>;
}

function StylizedCity({ heightData, gridSize, maxHeight, exaggeration, wireframe }: ReconstructionViewerProps & { exaggeration: number; wireframe: boolean }) {
  const regions = useMemo(() => extractBuildingRegions(heightData, gridSize, maxHeight), [gridSize, heightData, maxHeight]);
  const verticalScale = 3.6 / Math.max(maxHeight, 1) * exaggeration;

  return <group>
    <TerrainBase />
    {regions.map((region, index) => {
      const height = region.height * verticalScale;
      return <group key={`${region.centerX}-${region.centerZ}-${index}`} position={[region.centerX, height / 2, region.centerZ]}>
        <mesh castShadow receiveShadow>
          <boxGeometry args={[region.width, height, region.depth]} />
          <meshStandardMaterial color={wireframe ? "#9b94bd" : index % 3 === 0 ? "#c7cbd1" : "#b6beca"} roughness={0.77} wireframe={wireframe} />
        </mesh>
        {!wireframe && <mesh position={[0, height / 2 + 0.035, 0]} castShadow>
          <boxGeometry args={[region.width * 0.82, 0.07, region.depth * 0.82]} />
          <meshStandardMaterial color="#d8dbe0" roughness={0.7} />
        </mesh>}
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

function RgbSurface({ heightData, gridSize, maxHeight, exaggeration, inputImageUrl }: ReconstructionViewerProps & { exaggeration: number }) {
  const texture = useTexture(inputImageUrl);
  const geometry = useMemo(() => createSurfaceGeometry(heightData, gridSize, maxHeight, exaggeration), [exaggeration, gridSize, heightData, maxHeight]);

  return <mesh geometry={geometry} position={[0, 0.015, 0]}><meshBasicMaterial map={texture} polygonOffset polygonOffsetFactor={-1} polygonOffsetUnits={-1} /></mesh>;
}

function SceneContents({ heightData, gridSize, maxHeight, exaggeration, cameraMode, layers, inputImageUrl }: ReconstructionViewerProps & { exaggeration: number; cameraMode: CameraMode }) {
  const cameraPosition: [number, number, number] = cameraMode === "isometric" ? [12, 11, 14] : [0, 18, 0.01];

  return (
    <>
      <color attach="background" args={["#f0eff7"]} />
      <ambientLight intensity={1.6} />
      <directionalLight castShadow intensity={2.2} position={[7, 13, 8]} shadow-mapSize={[2048, 2048]} />
      <directionalLight intensity={0.55} position={[-8, 5, -4]} color="#d7d1ff" />
      {layers.city && <StylizedCity heightData={heightData} gridSize={gridSize} maxHeight={maxHeight} exaggeration={exaggeration} layers={layers} inputImageUrl={inputImageUrl} wireframe={layers.wireframe} />}
      <HeightSurface heightData={heightData} gridSize={gridSize} maxHeight={maxHeight} exaggeration={exaggeration} layers={layers} inputImageUrl={inputImageUrl} />
      {layers.rgb && <Suspense fallback={null}><RgbSurface heightData={heightData} gridSize={gridSize} maxHeight={maxHeight} exaggeration={exaggeration} layers={layers} inputImageUrl={inputImageUrl} /></Suspense>}
      <gridHelper args={[22, 22, "#d5d1e4", "#e5e3ed"]} position={[0, -0.04, 0]} />
      <OrbitControls makeDefault target={[0, 0.8, 0]} enableDamping dampingFactor={0.08} minDistance={5} maxDistance={28} maxPolarAngle={Math.PI * 0.48} />
      <PerspectiveCamera makeDefault position={cameraPosition} fov={36} near={0.1} far={100} />
    </>
  );
}

function ReconstructionViewer({ heightData, gridSize, maxHeight, layers, inputImageUrl }: ReconstructionViewerProps) {
  const [cameraMode, setCameraMode] = useState<CameraMode>("isometric");
  const [exaggeration, setExaggeration] = useState(1);
  const [resetKey, setResetKey] = useState(0);

  return (
    <div className="reconstruction-viewer">
      <Canvas key={`${cameraMode}-${resetKey}`} shadows dpr={[1, 2]} camera={{ position: [12, 11, 14], fov: 36 }}>
        <SceneContents heightData={heightData} gridSize={gridSize} maxHeight={maxHeight} exaggeration={exaggeration} cameraMode={cameraMode} layers={layers} inputImageUrl={inputImageUrl} />
      </Canvas>
      <div className="scene-toolbar" aria-label="Scene controls">
        <button className={cameraMode === "isometric" ? "selected" : ""} onClick={() => setCameraMode("isometric")}>Isometric</button>
        <button className={cameraMode === "top" ? "selected" : ""} onClick={() => setCameraMode("top")}>Top</button>
        <button onClick={() => setResetKey((key) => key + 1)}>Reset view</button>
        <label className="exaggeration-control">
          <span>Height {exaggeration.toFixed(1)}×</span>
          <input aria-label="Height exaggeration" type="range" min="1" max="3" step="0.1" value={exaggeration} onChange={(event) => setExaggeration(Number(event.target.value))} />
        </label>
      </div>
    </div>
  );
}

export { ReconstructionViewer };
