import { useState, type ReactNode } from "react";
import type { PredictionResult, SceneLayers } from "../types";

const API_BASE = "http://localhost:8000";

type PredictionInspectorProps = {
  prediction: PredictionResult;
  layers: SceneLayers;
  onToggleLayer: (layer: keyof SceneLayers) => void;
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

function PredictionInspector({ prediction, layers, onToggleLayer }: PredictionInspectorProps) {
  return (
    <aside className="prediction-inspector" aria-label="Prediction analysis inspector">
      <div className="inspector-title-row">
        <div><p className="eyebrow">Result details</p><h3>Inspector</h3></div>
        <span className="fixture-label">{prediction.isFixture ? "Fixture" : "Live model"}</span>
      </div>

      <InspectorSection title="Preview">
        <div className="inspector-previews">
          <figure><img src={`${API_BASE}${prediction.inputImageUrl}`} alt="Input RGB preview" /></figure>
          <figure><img src={`${API_BASE}${prediction.heightMapUrl}`} alt="Estimated nDSM preview" /></figure>
        </div>
      </InspectorSection>

      <InspectorSection title="Layers">
        <LayerToggle label="Stylized city" description="Primary scene" active={layers.city} onClick={() => onToggleLayer("city")} />
        <LayerToggle label="Estimated nDSM" description="Height surface" active={layers.height} onClick={() => onToggleLayer("height")} />
        <LayerToggle label="RGB relief" description="Optional terrain texture" active={layers.rgb} onClick={() => onToggleLayer("rgb")} />
        <LayerToggle label="Wireframe" description="Mesh structure" active={layers.wireframe} onClick={() => onToggleLayer("wireframe")} />
      </InspectorSection>

      <InspectorSection title="Analysis">
        <div className="inspector-metric-grid">
          <div><span>Input</span><strong>{prediction.width} × {prediction.height}</strong></div>
          <div><span>Scene</span><strong>{prediction.predictionWidth} × {prediction.predictionHeight}</strong></div>
          <div><span>Minimum</span><strong>{prediction.minHeight.toFixed(1)} m</strong></div>
          <div><span>Maximum</span><strong>{prediction.maxHeight.toFixed(1)} m</strong></div>
        </div>
        <div className="inspector-note">Accuracy metrics are available for reference-backed benchmark examples. This prediction is an estimated nDSM, not an absolute DSM.</div>
        <div className="inspector-note">Buildings: {prediction.buildingRegionSource === "semantic_head" ? "GAMUS semantic mask" : "height-derived fallback"} · {prediction.buildingRegions.length} regions</div>
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
