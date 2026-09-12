import type { BenchmarkResult } from "../types";

const API_BASE = "http://localhost:8000";

function BenchmarkWorkspace({ benchmark }: { benchmark: BenchmarkResult }) {
  const previews = [
    ["Input RGB", benchmark.inputImageUrl, "Input aerial image"],
    ["Ground-truth LiDAR nDSM", benchmark.groundTruthUrl, "Ground-truth LiDAR nDSM"],
    ["Predicted nDSM", benchmark.predictionUrl, "Predicted nDSM"],
    ["Error map", benchmark.errorMapUrl, "Prediction error map"],
  ] as const;

  return (
    <section className="benchmark-workspace" aria-label="Benchmark accuracy workspace">
      <div className="benchmark-header">
        <div><p className="eyebrow">Reference-backed comparison</p><h2>{benchmark.name}</h2></div>
        <div className="benchmark-source"><span className="status-dot online" /> {benchmark.sourceDataset} · {benchmark.split}</div>
      </div>
      <div className="benchmark-notice">Scaffold fixture metrics. Replace these assets with the held-out GAMUS validation tile before presenting results as measured model evidence.</div>
      <div className="benchmark-previews">
        {previews.map(([label, url, alt]) => <figure key={label}><img src={`${API_BASE}${url}`} alt={alt} /><figcaption>{label}</figcaption></figure>)}
      </div>
      <div className="benchmark-metrics" aria-label="Accuracy metrics">
        <div><span>RMSE</span><strong>{benchmark.metrics.rmse.toFixed(2)} m</strong><small>Root mean square error</small></div>
        <div><span>MAE</span><strong>{benchmark.metrics.mae.toFixed(2)} m</strong><small>Mean absolute error</small></div>
        <div><span>Correlation</span><strong>{benchmark.metrics.correlation.toFixed(2)}</strong><small>Pearson correlation</small></div>
      </div>
      {benchmark.comparison && <div className="benchmark-comparison" aria-label="Baseline comparison">
        <div><span>Retained baseline</span><strong>{benchmark.comparison.baseline.buildingBoundaryF1.toFixed(2)}</strong><small>Building-boundary F1</small></div>
        <div><span>Improved pipeline</span><strong>{benchmark.comparison.improved.buildingBoundaryF1.toFixed(2)}</strong><small>Building-boundary F1</small></div>
        <div><span>Coverage</span><strong>1024²</strong><small>Full-image target validation</small></div>
      </div>}
      <div className="benchmark-footer"><span>{benchmark.width} × {benchmark.height} reference tile</span><span>Metrics computed over aligned prediction and reference pixels</span></div>
    </section>
  );
}

export { BenchmarkWorkspace };
