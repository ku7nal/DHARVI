import { useEffect, useRef, useState } from "react";
import { BenchmarkWorkspace } from "./components/BenchmarkWorkspace";
import { PredictionInspector } from "./components/PredictionInspector";
import humanIcon from "./components/human.png";
import worldwideIcon from "./components/worldwide.png";
import { ReconstructionViewer } from "./scene/ReconstructionViewer";
import { appendGeoTiffCalibration, describeCalibration } from "./calibration";
import { createEvacuationBrief, expandDebrisZones, routePointToSceneCell } from "./routePlanner";
import { DEFAULT_SCENE_LAYERS, type BenchmarkResult, type EvacuationBrief, type PredictionResult, type RoutePoint, type RoutePoints, type RouteProfile, type RouteResult, type SceneLayers } from "./types";

type NavItem = "New reconstruction" | "Examples" | "About";
type PredictionState = "idle" | "processing" | "success" | "error";

const ACCEPTED_FORMATS = ".png,.jpg,.jpeg,.tif,.tiff";

function Icon({ name }: { name: "plus" | "layers" | "book" | "search" | "bell" | "chevron" }) {
  const paths = {
    plus: <><path d="M12 5v14M5 12h14" /></>,
    layers: <><path d="m12 3 8 4.5-8 4.5-8-4.5L12 3Z" /><path d="m4 12 8 4.5 8-4.5M4 16.5 12 21l8-4.5" /></>,
    book: <><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v16H6.5A2.5 2.5 0 0 0 4 21V5.5Z" /><path d="M4 5.5v15M8 7h8M8 11h8" /></>,
    search: <><circle cx="10.8" cy="10.8" r="6.8" /><path d="m16 16 4.5 4.5" /></>,
    bell: <><path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9ZM10 22h4" /></>,
    chevron: <path d="m8 10 4 4 4-4" />,
  };

  return (
    <svg aria-hidden="true" className="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      {paths[name]}
    </svg>
  );
}

function BrandMark() {
  return <div className="brand-mark" aria-hidden="true"><img src={worldwideIcon} alt="" /></div>;
}

function App() {
  const [activeNav, setActiveNav] = useState<NavItem>("New reconstruction");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [calibrateGeoTiff, setCalibrateGeoTiff] = useState(true);
  const [groundElevation, setGroundElevation] = useState("");
  const [groundElevationProvenance, setGroundElevationProvenance] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [backendStatus, setBackendStatus] = useState<"checking" | "online" | "offline">("checking");
  const [predictionState, setPredictionState] = useState<PredictionState>("idle");
  const [prediction, setPrediction] = useState<PredictionResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [layers, setLayers] = useState<SceneLayers>(DEFAULT_SCENE_LAYERS);
  const [benchmarks, setBenchmarks] = useState<BenchmarkResult[]>([]);
  const [benchmarkState, setBenchmarkState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [inspectorOpen, setInspectorOpen] = useState(true);
  const [route, setRoute] = useState<RouteResult | null>(null);
  const [routePoints, setRoutePoints] = useState<RoutePoints>({});
  const [routeSelectionMode, setRouteSelectionMode] = useState<"idle" | "start" | "destination" | "debris">("idle");
  const [pinPlacementActive, setPinPlacementActive] = useState(false);
  const [routeState, setRouteState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [routeError, setRouteError] = useState<string | null>(null);
  const [routeNotice, setRouteNotice] = useState<string | null>(null);
  const [avoidWater, setAvoidWater] = useState(true);
  const [debrisZones, setDebrisZones] = useState<RoutePoint[]>([]);
  const [routeProfile, setRouteProfile] = useState<RouteProfile>("fastest");
  const [demoSummary, setDemoSummary] = useState<{ baselineDistance: number; reroutedDistance: number; floodCell: RoutePoint } | null>(null);
  const routeRequestId = useRef(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetch("http://localhost:8000/api/health")
      .then((response) => {
        if (!response.ok) throw new Error("Backend unavailable");
        return response.json();
      })
      .then(() => setBackendStatus("online"))
      .catch(() => setBackendStatus("offline"));
  }, []);

  useEffect(() => {
    if (activeNav !== "Examples" || benchmarkState === "loading" || benchmarkState === "ready") return;
    setBenchmarkState("loading");
    fetch("http://localhost:8000/api/benchmarks")
      .then(async (response) => {
        const body = await response.json() as { benchmarks?: BenchmarkResult[]; detail?: string };
        if (!response.ok || !body.benchmarks?.length) throw new Error(body.detail ?? "Benchmark examples could not be loaded.");
        setBenchmarks(body.benchmarks);
        setBenchmarkState("ready");
      })
      .catch(() => setBenchmarkState("error"));
  }, [activeNav, benchmarkState]);

  function handleFile(file: File | undefined) {
    if (!file) return;
    setSelectedFile(file);
    void startPrediction(file, undefined, { enabled: calibrateGeoTiff, elevation: groundElevation, provenance: groundElevationProvenance });
  }

  async function startPrediction(file?: File, exampleId?: string, calibrationOptions = { enabled: true, elevation: "", provenance: "" }) {
    setPredictionState("processing");
    setPrediction(null);
    setErrorMessage(null);
    const formData = new FormData();
    if (file) formData.append("file", file);
    if (exampleId) formData.append("example_id", exampleId);
    if (file) appendGeoTiffCalibration(formData, file.name, calibrationOptions);

    try {
      const response = await fetch("http://localhost:8000/api/predict", { method: "POST", body: formData });
      const body = await response.json() as PredictionResult | { detail?: string };
      if (!response.ok) throw new Error("detail" in body ? body.detail : "Prediction could not be created.");
      const nextPrediction = body as PredictionResult;
      setPrediction(nextPrediction);
      setLayers(DEFAULT_SCENE_LAYERS);
      setRoute(null);
      setRoutePoints({});
      setRouteSelectionMode("idle");
      setPinPlacementActive(false);
      setRouteState("idle");
      setRouteError(null);
      setRouteNotice(null);
      setAvoidWater(true);
      setDebrisZones([]);
      setRouteProfile("fastest");
      setDemoSummary(null);
      if (exampleId === "gamus-urban-demo" && nextPrediction.semanticData?.length && nextPrediction.semanticGridSize) {
        const points = { start: { row: Math.round(nextPrediction.semanticGridSize * 0.47), column: 2 }, destination: { row: Math.round(nextPrediction.semanticGridSize * 0.47), column: nextPrediction.semanticGridSize - 4 } };
        setRoutePoints(points);
        void requestRoute(points, nextPrediction, [], true);
      }
      setSelectedFile(file ?? null);
      setInspectorOpen(true);
      setPredictionState("success");
    } catch (error) {
      setPredictionState("error");
      setErrorMessage(error instanceof Error ? error.message : "Prediction could not be created.");
    }
  }

  function selectRoutePoint(point: RoutePoint) {
    setRouteError(null);
    setRouteNotice(null);
    if (routeSelectionMode === "debris") {
      if (debrisZones.some((zone) => zone.row === point.row && zone.column === point.column)) return;
      const nextZones = [...debrisZones, point];
      setDebrisZones(nextZones);
      setRouteSelectionMode("idle");
      if (routePoints.start && routePoints.destination) void requestRoute(routePoints, prediction, nextZones, avoidWater, "Route recalculated around the new debris zone.");
      return;
    }
    setRoute(null);
    const selectedClass = prediction?.semanticData && prediction.semanticGridSize
      ? prediction.semanticData[point.row * prediction.semanticGridSize + point.column]
      : undefined;
    if (selectedClass !== 5) {
      setRouteError("Select a point on a semantic road cell.");
      setRouteState("error");
      return;
    }
    if (routeSelectionMode === "start") {
      setRoutePoints((current) => ({ ...current, start: point }));
    } else if (routeSelectionMode === "destination") {
      setRoutePoints((current) => ({ ...current, destination: point }));
    }
    setRouteSelectionMode("idle");
    setRouteState("idle");
  }

  function changeRouteSelectionMode(mode: "idle" | "start" | "destination" | "debris") {
    setRouteSelectionMode(mode);
    if (mode !== "idle") setPinPlacementActive(false);
  }

  async function requestRoute(points = routePoints, sourcePrediction = prediction, zones = debrisZones, waterAvoidance = avoidWater, notice?: string, selectedProfile = routeProfile) {
    if (!sourcePrediction?.semanticData?.length || !sourcePrediction.semanticGridSize || !points.start || !points.destination) return;
    const requestId = routeRequestId.current + 1;
    routeRequestId.current = requestId;
    setRouteState("loading");
    setRouteError(null);
    setRouteNotice(null);
    try {
      const response = await fetch("http://localhost:8000/api/route", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ semanticData: sourcePrediction.semanticData, gridSize: sourcePrediction.semanticGridSize, start: points.start, destination: points.destination, blockedCells: expandDebrisZones(zones, sourcePrediction.semanticGridSize), avoidWater: waterAvoidance, profile: selectedProfile, heightData: sourcePrediction.heightData, uncertaintyData: sourcePrediction.boundaryData?.length === sourcePrediction.semanticGridSize ** 2 ? sourcePrediction.boundaryData.map((value) => Math.min(value, 1 - value) * 2) : undefined }),
      });
      const body = await response.json() as RouteResult | { detail?: string };
      if (!response.ok) throw new Error("detail" in body ? body.detail : "Route could not be generated.");
      if (requestId !== routeRequestId.current) return;
      setRoute(body as RouteResult);
      setRoutePoints({ start: (body as RouteResult).start, destination: (body as RouteResult).destination });
      setRouteState("ready");
      setRouteNotice(notice ?? null);
    } catch (error) {
      if (requestId !== routeRequestId.current) return;
      setRoute(null);
      setRouteState("error");
      setRouteNotice(null);
      setRouteError(error instanceof Error ? error.message : "Route could not be generated.");
    }
  }

  async function loadDemoRoute() {
    if (!prediction?.semanticGridSize) return;
    const requestId = routeRequestId.current + 1;
    routeRequestId.current = requestId;
    setRoute(null);
    setDemoSummary(null);
    setRouteState("loading");
    setRouteError(null);
    try {
      const response = await fetch("http://localhost:8000/api/route/demo");
      const body = await response.json() as { baseline?: RouteResult; rerouted?: RouteResult; debrisZone?: RoutePoint; floodCell?: RoutePoint } | { detail?: string };
      if (!response.ok || !("baseline" in body) || !body.baseline || !body.rerouted || !body.debrisZone || !body.floodCell) throw new Error("The deterministic demo could not be loaded.");
      if (requestId !== routeRequestId.current) return;
      const scenePoint = routePointToSceneCell(body.debrisZone, body.rerouted.gridSize, prediction.semanticGridSize);
      const sceneStart = routePointToSceneCell(body.rerouted.start, body.rerouted.gridSize, prediction.semanticGridSize);
      const sceneDestination = routePointToSceneCell(body.rerouted.destination, body.rerouted.gridSize, prediction.semanticGridSize);
      setRoute(body.rerouted);
      setRoutePoints({ start: sceneStart, destination: sceneDestination });
      setDebrisZones([scenePoint]);
      setDemoSummary({ baselineDistance: body.baseline.distanceCells, reroutedDistance: body.rerouted.distanceCells, floodCell: body.floodCell });
      setRouteState("ready");
      setRouteNotice(`Demo replay: baseline ${body.baseline.distanceCells} cells → flood/debris reroute ${body.rerouted.distanceCells} cells.`);
    } catch (error) {
      if (requestId !== routeRequestId.current) return;
      setRoute(null);
      setDemoSummary(null);
      setRouteState("error");
      setRouteError(error instanceof Error ? error.message : "The deterministic demo could not be loaded.");
    }
  }

  function toggleWaterAvoidance() {
    const nextAvoidWater = !avoidWater;
    setAvoidWater(nextAvoidWater);
    if (routePoints.start && routePoints.destination) void requestRoute(routePoints, prediction, debrisZones, nextAvoidWater, nextAvoidWater ? "Route recalculated with detected water excluded." : "Water exclusion disabled; review the route carefully.");
  }

  function clearDebrisZones() {
    setDebrisZones([]);
    if (routePoints.start && routePoints.destination) void requestRoute(routePoints, prediction, [], avoidWater, "Route recalculated after clearing debris zones.");
  }

  function removeDebrisZone(index: number) {
    const nextZones = debrisZones.filter((_, zoneIndex) => zoneIndex !== index);
    setDebrisZones(nextZones);
    if (routePoints.start && routePoints.destination) void requestRoute(routePoints, prediction, nextZones, avoidWater, "Route recalculated after removing a debris zone.");
  }

  function changeRouteProfile(profile: RouteProfile) {
    setRouteProfile(profile);
    if (routePoints.start && routePoints.destination) void requestRoute(routePoints, prediction, debrisZones, avoidWater, `${profile[0].toUpperCase()}${profile.slice(1)} route selected.`, profile);
  }

  function exportRouteBrief() {
    if (!route || !prediction) return;
    const brief: EvacuationBrief = createEvacuationBrief(route, prediction);
    const url = URL.createObjectURL(new Blob([JSON.stringify(brief, null, 2)], { type: "application/json" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `evacuation-brief-${route.profile}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  const statusLabel = backendStatus === "online" ? "API connected" : backendStatus === "offline" ? "API offline" : "Checking API";
  const hasResult = activeNav === "New reconstruction" && predictionState === "success" && Boolean(prediction);

  return (
    <main className="page-shell">
      <section className={`app-window ${sidebarCollapsed ? "sidebar-collapsed" : ""}`} aria-label="DepthWizard workspace">
        <aside className="sidebar">
          <div className="brand-row">
            <BrandMark />
            <span className="brand-name">DepthWizard</span>
            <button
              className="icon-button sidebar-collapse"
              aria-label={sidebarCollapsed ? "Expand navigation" : "Collapse navigation"}
              aria-expanded={!sidebarCollapsed}
              onClick={() => setSidebarCollapsed((collapsed) => !collapsed)}
            >
              <Icon name="chevron" />
            </button>
          </div>

          <nav className="navigation" aria-label="Main navigation">
            <p className="nav-label">Workspace</p>
            <button className={`nav-item ${activeNav === "New reconstruction" ? "active" : ""}`} onClick={() => setActiveNav("New reconstruction")}>
              <Icon name="plus" />
              <span>New reconstruction</span>
            </button>
            <button
              className={`nav-item ${hasResult && inspectorOpen ? "active" : activeNav === "Examples" ? "active" : ""}`}
              onClick={() => hasResult ? setInspectorOpen((open) => !open) : setActiveNav("Examples")}
              aria-label={hasResult ? (inspectorOpen ? "Close layers inspector" : "Open layers inspector") : "Examples"}
            >
              <Icon name="layers" />
              <span>Examples</span>
            </button>
            <button className={`nav-item ${activeNav === "About" ? "active" : ""}`} onClick={() => setActiveNav("About")}>
              <Icon name="book" />
              <span>About</span>
            </button>
          </nav>

          <div className="sidebar-footer">
            <span className={`status-dot ${backendStatus}`} />
            <span>{statusLabel}</span>
            <span className="version-label">v0.1</span>
          </div>
        </aside>

        <div className="workspace">
          <div className="workspace-content">
            <div className="floating-actions" aria-label="Workspace actions">
              <span className="team-label">Team Drishtikon</span>
              <button className="avatar-button" aria-label="User profile">
                <img src={humanIcon} alt="" />
              </button>
            </div>
            <div className="content-heading">
              <div>
                <p className="eyebrow">Monocular height reconstruction</p>
                <h1>{activeNav === "New reconstruction" ? "New reconstruction" : activeNav}</h1>
              </div>
                <div className="content-meta">{prediction ? describeCalibration(prediction.heightReference, prediction.calibration).reference : "Estimated nDSM · relative meters"}</div>
            </div>

            {activeNav === "New reconstruction" && predictionState === "success" && prediction ? (
              <section className="result-card">
                <div className={`result-body ${inspectorOpen ? "" : "inspector-closed"}`}>
                  <ReconstructionViewer
                    heightData={prediction.heightData}
                    validityData={prediction.validityData}
                    gridSize={prediction.gridSize}
                    maxHeight={prediction.maxHeight}
                    heightReference={prediction.heightReference}
                    buildingRegions={prediction.buildingRegions}
                    semanticData={prediction.semanticData}
                    semanticGridSize={prediction.semanticGridSize}
                    semanticClasses={prediction.semanticClasses}
                    route={route}
                    routePoints={routePoints}
                    routeSelectionMode={routeSelectionMode}
                    onRoutePointSelect={selectRoutePoint}
                    pinPlacementActive={pinPlacementActive}
                    onPinPlacementActiveChange={(active) => {
                      setPinPlacementActive(active);
                      if (active) setRouteSelectionMode("idle");
                    }}
                    debrisZones={debrisZones}
                    layers={layers}
                    inputImageUrl={`http://localhost:8000${prediction.inputImageUrl}`}
                  />
                  <PredictionInspector
                      isOpen={inspectorOpen}
                      prediction={prediction}
                      layers={layers}
                      onToggleLayer={(layer) => setLayers((current) => ({ ...current, [layer]: !current[layer] }))}
                      onClose={() => setInspectorOpen(false)}
                      route={route}
                      routePoints={routePoints}
                      routeSelectionMode={routeSelectionMode}
                      routeState={routeState}
                      routeError={routeError}
                      routeNotice={routeNotice}
                      avoidWater={avoidWater}
                      debrisZones={debrisZones}
                      onRouteModeChange={changeRouteSelectionMode}
                      onToggleWater={toggleWaterAvoidance}
                      onClearDebris={clearDebrisZones}
                      onRemoveDebris={removeDebrisZone}
                      routeProfile={routeProfile}
                      onRouteProfileChange={changeRouteProfile}
                      onExportBrief={exportRouteBrief}
                      demoSummary={demoSummary}
                      onPlanRoute={() => void requestRoute()}
                      onLoadDemoRoute={loadDemoRoute}
                      onClearRoute={() => { setRoute(null); setRoutePoints({}); setRouteState("idle"); setRouteError(null); }}
                    />
                </div>
              </section>
            ) : activeNav === "New reconstruction" && (
              <section
                className={`upload-card ${isDragging ? "dragging" : ""}`}
                onDragEnter={(event) => { event.preventDefault(); setIsDragging(true); }}
                onDragOver={(event) => event.preventDefault()}
                onDragLeave={() => setIsDragging(false)}
                onDrop={(event) => { event.preventDefault(); setIsDragging(false); handleFile(event.dataTransfer.files[0]); }}
                aria-label="Upload aerial image"
              >
                <div className="upload-illustration"><span className="upload-orbit orbit-one" /><span className="upload-orbit orbit-two" /><span className="upload-core"><Icon name="plus" /></span></div>
                {predictionState === "processing" ? <>
                  <h2>Preparing your reconstruction</h2>
                  <p>Running the fine-tuned DepthAnything V2 model.</p>
                  <div className="progress-track"><span /></div>
                </> : predictionState === "error" ? <>
                  <h2>We could not process that image</h2>
                  <p className="error-copy">{errorMessage}</p>
                  <button className="primary-button" onClick={() => fileInputRef.current?.click()}><Icon name="plus" /> Try another image</button>
                </> : <>
                  <h2>Bring a scene to life</h2>
                  <p>Upload an aerial image to generate an explorable 3D scene.</p>
                  <div className="calibration-options">
                    <label><input type="checkbox" checked={calibrateGeoTiff} onChange={(event) => setCalibrateGeoTiff(event.target.checked)} /> Calibrate GeoTIFF when evidence is available</label>
                    <small>Without calibration, or with insufficient ground evidence, the result stays a relative height estimate.</small>
                    {calibrateGeoTiff && <>
                      <label htmlFor="ground-elevation">Known ground elevation (meters, optional)</label>
                      <input id="ground-elevation" type="number" step="any" value={groundElevation} onChange={(event) => setGroundElevation(event.target.value)} placeholder="e.g. 120.5" />
                      {groundElevation.trim() && <>
                        <label htmlFor="ground-elevation-provenance">Elevation source (optional)</label>
                        <input id="ground-elevation-provenance" value={groundElevationProvenance} onChange={(event) => setGroundElevationProvenance(event.target.value)} placeholder="e.g. survey benchmark" />
                      </>}
                    </>}
                  </div>
                  <button className="primary-button" onClick={() => fileInputRef.current?.click()}>
                    <Icon name="plus" /> Upload aerial image
                  </button>
                </>}
                <input ref={fileInputRef} className="visually-hidden" type="file" accept={ACCEPTED_FORMATS} onChange={(event) => handleFile(event.target.files?.[0])} />
                <div className="supported-formats"><span>PNG</span><span>JPEG</span><span>RGB GeoTIFF</span></div>
                <button className="text-button" onClick={() => void startPrediction(undefined, "gamus-urban-demo")}>Try a GAMUS example <span>→</span></button>
              </section>
            )}

            {activeNav === "Examples" && (benchmarkState === "ready" && benchmarks.length ? <BenchmarkWorkspace benchmarks={benchmarks} /> : <section className="empty-panel"><div className="panel-icon"><Icon name="layers" /></div><h2>{benchmarkState === "error" ? "Benchmark unavailable" : "Loading benchmark examples"}</h2><p>{benchmarkState === "error" ? "Start the backend and try again to load reference comparisons." : "Preparing input, reference, prediction, error map, and accuracy metrics."}</p>{benchmarkState === "error" && <button className="primary-button" onClick={() => setBenchmarkState("idle")}>Try again</button>}</section>)}
            {activeNav === "About" && <section className="empty-panel"><div className="panel-icon"><Icon name="book" /></div><h2>About DepthWizard</h2><p>Explore estimated height above ground from aerial imagery. The first workspace is designed around a fine-tuned DepthAnything V2 model trained on GAMUS.</p></section>}
          </div>
        </div>
      </section>
    </main>
  );
}

export { App };
