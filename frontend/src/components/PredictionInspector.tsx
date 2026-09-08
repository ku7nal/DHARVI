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
        <span className="fixture-label">Fixture</span>
      </div>

      <InspectorSection title="Scene">
        <div className="inspector-stat"><span>Model</span><strong>DepthAnything V2 Small</strong></div>
        <div className="inspector-stat"><span>Fine-tuning</span><strong>GAMUS</strong></div>
        <div className="inspector-stat"><span>Result</span><strong>Estimated nDSM</strong></div>
        <div className="inspector-stat"><span>Unit</span><strong>meters</strong></div>
      </InspectorSection>

      <InspectorSection title="Layers">
        <LayerToggle label="Stylized city" description="Primary scene" active={layers.city} onClick={() => onToggleLayer("city")} />
        <LayerToggle label="Estimated nDSM" description="Height surface" active={layers.height} onClick={() => onToggleLayer("height")} />
        <LayerToggle label="RGB texture" description="Input imagery" active={layers.rgb} onClick={() => onToggleLayer("rgb")} />
        <LayerToggle label="Wireframe" description="Mesh structure" active={layers.wireframe} onClick={() => onToggleLayer("wireframe")} />
      </InspectorSection>

      <InspectorSection title="Analysis">
        <div className="inspector-metric-grid">
          <div><span>Input</span><strong>{prediction.width} × {prediction.height}</strong></div>
          <div><span>Scene</span><strong>{prediction.predictionWidth} × {prediction.predictionHeight}</strong></div>
          <div><span>Minimum</span><strong>{prediction.minHeight.toFixed(1)} m</strong></div>
          <div><span>Maximum</span><strong>{prediction.maxHeight.toFixed(1)} m</strong></div>
        </div>
        <div className="inspector-note">Accuracy metrics are available for reference-backed benchmark examples. This fixture has no ground-truth comparison.</div>
      </InspectorSection>

      <InspectorSection title="Preview" defaultOpen={false}>
        <div className="inspector-previews">
          <figure><img src={`${API_BASE}${prediction.inputImageUrl}`} alt="Input RGB preview" /><figcaption>Input RGB</figcaption></figure>
          <figure><img src={`${API_BASE}${prediction.heightMapUrl}`} alt="Estimated nDSM preview" /><figcaption>Estimated nDSM</figcaption></figure>
        </div>
      </InspectorSection>
    </aside>
  );
}

export { PredictionInspector };
