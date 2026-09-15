import { useState, type ReactNode } from "react";
import type { PredictionResult, RoutePoint, RoutePoints, RouteResult, SceneLayers } from "../types";

const API_BASE = "http://localhost:8000";

type PredictionInspectorProps = {
  isOpen: boolean;
  prediction: PredictionResult;
  layers: SceneLayers;
  onToggleLayer: (layer: keyof SceneLayers) => void;
  onClose: () => void;
  route: RouteResult | null;
  routePoints: RoutePoints;
  routeSelectionMode: "idle" | "start" | "destination" | "debris";
  routeState: "idle" | "loading" | "ready" | "error";
  routeError: string | null;
  routeNotice: string | null;
  avoidWater: boolean;
  debrisZones: RoutePoint[];
  onRouteModeChange: (mode: "idle" | "start" | "destination" | "debris") => void;
  onPlanRoute: () => void;
  onLoadDemoRoute: () => void;
  onClearRoute: () => void;
  onToggleWater: () => void;
  onClearDebris: () => void;
  onRemoveDebris: (index: number) => void;
};

function InspectorSection({ title, children, defaultOpen = true }: { title: string; children: ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <section className="inspector-section">
      <button className="inspector-section-header" onClick={() => setOpen((value) => !value)} aria-expanded={open}>
        <span>{title}</span>
        <span className={`inspector-chevron ${open ? "open" : ""}`}>⌄</span>
      </button>
      {open && <div className="inspector-section-body">{children}</div>}
    </section>
  );
}

function LayerToggle({ label, description, active, onClick }: { label: string; description: string; active: boolean; onClick: () => void }) {
  return (
    <button className={`layer-toggle ${active ? "active" : ""}`} onClick={onClick} aria-pressed={active}>
      <span className={`layer-switch ${active ? "active" : ""}`} aria-hidden="true"><span /></span>
      <span className="layer-copy"><strong>{label}</strong><small>{description}</small></span>
    </button>
  );
}

function PredictionInspector({ isOpen, prediction, layers, onToggleLayer, onClose, route, routePoints, routeSelectionMode, routeState, routeError, routeNotice, avoidWater, debrisZones, onRouteModeChange, onPlanRoute, onLoadDemoRoute, onClearRoute, onToggleWater, onClearDebris, onRemoveDebris }: PredictionInspectorProps) {
  const semanticPayloadAligned = Boolean(
    prediction.semanticGridSize &&
    prediction.semanticGridSize === prediction.gridSize &&
    prediction.semanticData?.length === prediction.semanticGridSize ** 2,
  );
  const semanticAvailable = Boolean(prediction.semanticMapUrl && prediction.semanticClasses?.length && semanticPayloadAligned);
  const semanticSourceLabel = prediction.semanticSource === "fixture"
    ? "Fixture semantic labels"
    : prediction.semanticSource === "trained"
      ? "Trained GAMUS semantic head"
      : "Height-only fallback semantics";

  return (
    <aside className={`prediction-inspector ${isOpen ? "" : "is-closed"}`} aria-label="Prediction analysis inspector" aria-hidden={!isOpen}>
      <div className="inspector-reference-header">
        <span className="inspector-reference-title">Inspector</span>
        <button className="inspector-close" onClick={onClose} aria-label="Collapse layers inspector">
          <svg className="inspector-collapse-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="m15 5-7 7 7 7" />
          </svg>
        </button>
      </div>

      <InspectorSection title="Preview">
        <div className="inspector-previews">
          <figure><img src={`${API_BASE}${prediction.inputImageUrl}`} alt="Input RGB preview" /></figure>
          <figure><img src={`${API_BASE}${prediction.heightMapUrl}`} alt="Estimated nDSM preview" /></figure>
        </div>
      </InspectorSection>

      <InspectorSection title="Semantics">
        <div className={`semantic-source ${semanticAvailable ? "available" : "unavailable"}`}>
          <span className="status-dot" /> {semanticSourceLabel}
        </div>
        {semanticAvailable ? <>
          <img className="semantic-preview" src={`${API_BASE}${prediction.semanticMapUrl}`} alt={`GAMUS semantic class mask, aligned ${prediction.semanticGridSize} by ${prediction.semanticGridSize} grid`} />
          <div className="semantic-legend">
            {prediction.semanticClasses?.map((semanticClass) => <div key={semanticClass.id} className="semantic-legend-item">
              <span className="semantic-swatch" style={{ backgroundColor: semanticClass.color }} />
              <span>{semanticClass.label}</span>
            </div>)}
          </div>
          <small className="semantic-note">Aligned {prediction.semanticGridSize} × {prediction.semanticGridSize} categorical class mask. Height preview is continuous.</small>
        </> : <div className="inspector-note">{prediction.semanticData?.length && !semanticPayloadAligned
          ? "Semantic preview is unavailable because its class grid is not aligned with the scene grid."
          : "This result contains height data only. Building and terrain layers use height-derived fallback behavior until semantic labels are available."}</div>}
      </InspectorSection>

      <InspectorSection title="Layers">
        <LayerToggle label="Stylized city" description="Primary scene" active={layers.city} onClick={() => onToggleLayer("city")} />
        <LayerToggle label="Buildings" description="Clean footprint extrusions" active={layers.buildings} onClick={() => onToggleLayer("buildings")} />
        <LayerToggle label="Ground" description="Smoothed terrain" active={layers.ground} onClick={() => onToggleLayer("ground")} />
        <LayerToggle label="Roads" description="Stable road surfaces" active={layers.roads} onClick={() => onToggleLayer("roads")} />
        <LayerToggle label="Water" description="Stable water surfaces" active={layers.water} onClick={() => onToggleLayer("water")} />
        <LayerToggle label="Vegetation" description="Low-poly green cover" active={layers.vegetation} onClick={() => onToggleLayer("vegetation")} />
        <LayerToggle label="Trees" description="Bounded tree geometry" active={layers.trees} onClick={() => onToggleLayer("trees")} />
        <LayerToggle label="Estimated nDSM" description="Height surface" active={layers.height} onClick={() => onToggleLayer("height")} />
        <LayerToggle label="Slope" description="Terrain gradient heatmap" active={layers.slope} onClick={() => onToggleLayer("slope")} />
        <LayerToggle label="RGB relief" description="Optional terrain texture" active={layers.rgb} onClick={() => onToggleLayer("rgb")} />
        <LayerToggle label="Wireframe" description="Mesh structure" active={layers.wireframe} onClick={() => onToggleLayer("wireframe")} />
      </InspectorSection>

      <InspectorSection title="Evacuation route">
        {semanticAvailable ? <>
          <div className="route-intro">Plan a road-only emergency route from this semantic reconstruction.</div>
          <div className="route-points">
            <div><span className="route-marker-dot origin" />Origin <strong>{routePoints.start ? `${routePoints.start.row}, ${routePoints.start.column}` : "Not set"}</strong></div>
            <div><span className="route-marker-dot destination" />Destination <strong>{routePoints.destination ? `${routePoints.destination.row}, ${routePoints.destination.column}` : "Not set"}</strong></div>
          </div>
          <div className="route-actions">
            <button className={`route-button ${routeSelectionMode === "start" ? "active" : ""}`} onClick={() => onRouteModeChange("start")}>Select origin</button>
            <button className={`route-button ${routeSelectionMode === "destination" ? "active" : ""}`} onClick={() => onRouteModeChange("destination")}>Select destination</button>
          </div>
          <div className="route-actions hazard-actions">
            <button className={`route-button hazard-button ${avoidWater ? "active" : ""}`} onClick={onToggleWater}>Water hazards {avoidWater ? "on" : "off"}</button>
            <button className={`route-button hazard-button ${routeSelectionMode === "debris" ? "active" : ""}`} onClick={() => onRouteModeChange("debris")}>Mark debris area</button>
          </div>
          <div className="route-hazard-summary"><span>{debrisZones.length} debris zone{debrisZones.length === 1 ? "" : "s"}</span>{debrisZones.length > 0 && <button className="text-button" onClick={onClearDebris}>Clear all</button>}</div>
          {debrisZones.length > 0 && <div className="debris-zone-list">{debrisZones.map((zone, index) => <div key={`${zone.row}:${zone.column}`}><span>Zone {index + 1} · {zone.row}, {zone.column} · 3×3</span><button className="text-button" onClick={() => onRemoveDebris(index)}>Remove</button></div>)}</div>}
          <button className="primary-button route-plan-button" disabled={!routePoints.start || !routePoints.destination || routeState === "loading"} onClick={onPlanRoute}>{routeState === "loading" ? "Planning route…" : "Plan evacuation route"}</button>
          <button className="text-button route-demo-button" onClick={onLoadDemoRoute}>Load demo route <span>→</span></button>
          {routeSelectionMode !== "idle" && <div className="route-hint">Click the scene to {routeSelectionMode === "start" ? "set the origin on a road" : routeSelectionMode === "destination" ? "set the destination on a road" : "mark a temporary debris zone"}.</div>}
          {routeState === "error" && <div className="route-error">{routeError}</div>}
          {routeNotice && <div className="route-hint">{routeNotice}</div>}
          {route && <div className="route-result"><strong>Route ready</strong><span>{route.distanceCells} road cells · {route.path.length} waypoints</span><span>{route.hazards.waterAvoidance ? `${route.hazards.waterCells} detected water cells excluded · ${route.hazards.waterBlockedRoadCells} road cells near water blocked` : "Water exclusion disabled"} · {route.hazards.blockedRoadCells} road cells blocked by debris</span><button className="text-button" onClick={onClearRoute}>Clear route</button></div>}
        </> : <div className="inspector-note">Evacuation routing requires an aligned semantic road mask. Use the GAMUS example to try the deterministic route demo.</div>}
      </InspectorSection>

      <InspectorSection title="Analysis">
        <div className="inspector-metric-grid">
          <div><span>Input</span><strong>{prediction.width} × {prediction.height}</strong></div>
          <div><span>Scene</span><strong>{prediction.predictionWidth} × {prediction.predictionHeight}</strong></div>
          <div><span>Minimum</span><strong>{prediction.minHeight.toFixed(1)} m</strong></div>
          <div><span>Maximum</span><strong>{prediction.maxHeight.toFixed(1)} m</strong></div>
        </div>
        <div className="inspector-note">{prediction.heightReference === "absolute" ? "Metric DSM calibrated to the source GeoTIFF reference." : "This prediction is an estimated nDSM with relative height values, not an absolute DSM."}</div>
        {prediction.calibration && prediction.calibration.status !== "not_applicable" && <div className="inspector-note">Calibration: {prediction.calibration.status.replaceAll("_", " ")} · confidence {prediction.calibration.confidence === null ? "—" : `${(prediction.calibration.confidence * 100).toFixed(0)}%`} · residual {prediction.calibration.residualError === null ? "—" : `${prediction.calibration.residualError.toFixed(2)} m`}</div>}
        {prediction.boundarySource === "trained"
          ? <div className="inspector-note">CNN boundary refinement active · confidence {prediction.boundaryConfidence === null || prediction.boundaryConfidence === undefined ? "—" : `${(prediction.boundaryConfidence * 100).toFixed(0)}%`}</div>
          : <div className="inspector-note">CNN boundary refinement unavailable; building footprints use semantic labels only.</div>}
        {prediction.dsmUrl && <a className="text-button" href={`${API_BASE}${prediction.dsmUrl}`} download>Download metric DSM GeoTIFF</a>}
        <div className="inspector-note">Buildings: {prediction.buildingRegionSource === "semantic_head" ? "GAMUS semantic mask" : "height-derived fallback"} · {prediction.buildingRegions?.length ?? 0} regions</div>
        {prediction.geospatial && <div className="geospatial-card">
          <strong>GeoTIFF metadata</strong>
          <div className="inspector-stat"><span>CRS</span><strong>{prediction.geospatial.crs ?? "Not defined"}</strong></div>
          <div className="inspector-stat"><span>Resolution</span><strong>{prediction.geospatial.resolution[0]} × {prediction.geospatial.resolution[1]}</strong></div>
          <div className="inspector-stat"><span>Bands</span><strong>{prediction.geospatial.bands}</strong></div>
          {prediction.geospatial.validPixelFraction !== undefined && <div className="inspector-stat"><span>Valid pixels</span><strong>{(prediction.geospatial.validPixelFraction * 100).toFixed(1)}%</strong></div>}
          <div className="inspector-stat"><span>Bounds</span><strong>{prediction.geospatial.bounds.left.toFixed(4)}, {prediction.geospatial.bounds.bottom.toFixed(4)} → {prediction.geospatial.bounds.right.toFixed(4)}, {prediction.geospatial.bounds.top.toFixed(4)}</strong></div>
          <small>Rendered in local scene coordinates.</small>
        </div>}
      </InspectorSection>

    </aside>
  );
}

export { PredictionInspector };
