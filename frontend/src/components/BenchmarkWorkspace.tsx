import { useState } from "react";
import type { BenchmarkResult } from "../types";

const API_BASE = "http://localhost:8000";

function BenchmarkWorkspace({ benchmarks }: { benchmarks: BenchmarkResult[] }) {
  const [selectedGroup, setSelectedGroup] = useState(benchmarks[0]?.landscapeGroup ?? "urban");
  const benchmark = benchmarks.find((item) => item.landscapeGroup === selectedGroup) ?? benchmarks[0];
  const comparison = benchmark.comparison;
  const isValidatedMetric = benchmark.referenceStatus === "validated" && benchmark.heightReference === "metric";
  const referenceLabel = isValidatedMetric ? "Ground-truth metric DSM" : "Relative reference fixture";
  const previews = [
    ["Input RGB", benchmark.inputImageUrl, "Input aerial image"],
    [referenceLabel, benchmark.groundTruthUrl, referenceLabel],
    ["Predicted nDSM", benchmark.predictionUrl, "Predicted nDSM"],
    ["Error map", benchmark.errorMapUrl, "Prediction error map"],
  ] as const;

  return (
    <section className="benchmark-workspace" aria-label="Benchmark accuracy workspace">
      <div className="benchmark-header">
        <div><p className="eyebrow">Reference-backed comparison</p><h2>{benchmark.name}</h2></div>
        <div className="benchmark-source"><span className="status-dot online" /> {benchmark.sourceDataset} · {benchmark.split}</div>
      </div>
      <div className="benchmark-groups" aria-label="Landscape validation groups">
        {benchmarks.map((item) => <button className={item.landscapeGroup === benchmark.landscapeGroup ? "benchmark-group-button active" : "benchmark-group-button"} key={item.id} onClick={() => setSelectedGroup(item.landscapeGroup)}>{item.landscapeGroup}</button>)}
      </div>
      <div className={isValidatedMetric ? "benchmark-notice validated" : "benchmark-notice"}>{isValidatedMetric ? "Validated metric DSM: errors are reported against aligned survey heights." : benchmark.coverageNote}</div>
      <div className="benchmark-previews">
        {previews.map(([label, url, alt]) => <figure key={label}><img src={`${API_BASE}${url}`} alt={alt} /><figcaption>{label}</figcaption></figure>)}
      </div>
      <div className="benchmark-metrics" aria-label="Accuracy metrics">
        <div><span>RMSE</span><strong>{benchmark.metrics.rmse.toFixed(2)} m</strong><small>Root mean square error</small></div>
        <div><span>MAE</span><strong>{benchmark.metrics.mae.toFixed(2)} m</strong><small>Mean absolute error</small></div>
        <div><span>Correlation</span><strong>{benchmark.metrics.correlation.toFixed(2)}</strong><small>Pearson correlation</small></div>
        <div><span>Semantic mIoU</span><strong>{benchmark.metrics.semanticMiou.toFixed(2)}</strong><small>Mean class intersection over union</small></div>
        <div><span>Building IoU</span><strong>{benchmark.metrics.buildingIoU.toFixed(2)}</strong><small>Building footprint overlap</small></div>
        <div><span>Boundary F1</span><strong>{benchmark.metrics.buildingBoundaryF1.toFixed(2)}</strong><small>Building-boundary agreement</small></div>
      </div>
      {comparison && <div className="benchmark-comparison" aria-label="Baseline comparison">
        {(["rmse", "mae", "correlation", "semanticMiou", "buildingIoU", "buildingBoundaryF1"] as const).map((metric) => <div key={metric}>
          <span>{{ rmse: "RMSE", mae: "MAE", correlation: "Correlation", semanticMiou: "Semantic mIoU", buildingIoU: "Building IoU", buildingBoundaryF1: "Boundary F1" }[metric]}</span>
          <strong>{comparison.baseline[metric].toFixed(2)} → {comparison.improved[metric].toFixed(2)}</strong>
          <small>Retained baseline → improved pipeline</small>
        </div>)}
      </div>}
      <div className="benchmark-footer"><span>{benchmark.width} × {benchmark.height} · {benchmark.landscapeGroup} · {benchmark.heightReference} heights</span><span>{benchmark.knownLimitations.join(" ")}</span></div>
    </section>
  );
}

export { BenchmarkWorkspace };
