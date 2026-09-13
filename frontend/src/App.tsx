import { useEffect, useRef, useState } from "react";
import { BenchmarkWorkspace } from "./components/BenchmarkWorkspace";
import { PredictionInspector } from "./components/PredictionInspector";
import { ReconstructionViewer } from "./scene/ReconstructionViewer";
import { DEFAULT_SCENE_LAYERS, type BenchmarkResult, type PredictionResult, type SceneLayers } from "./types";

type NavItem = "New reconstruction" | "Examples" | "About";
type ReferenceNavItem = "Home" | "Products" | "Industries" | "Company" | "Resources";
type PredictionState = "idle" | "processing" | "success" | "error";

const ACCEPTED_FORMATS = ".png,.jpg,.jpeg,.tif,.tiff";

function Icon({ name }: { name: "plus" | "layers" | "book" }) {
  const paths = {
    plus: <><path d="M12 5v14M5 12h14" /></>,
    layers: <><path d="m12 3 8 4.5-8 4.5-8-4.5L12 3Z" /><path d="m4 12 8 4.5 8-4.5M4 16.5 12 21l8-4.5" /></>,
    book: <><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v16H6.5A2.5 2.5 0 0 0 4 21V5.5Z" /><path d="M4 5.5v15M8 7h8M8 11h8" /></>,
  };

  return (
    <svg aria-hidden="true" className="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      {paths[name]}
    </svg>
  );
}

function BrandMark() {
  return <div className="brand-mark" aria-hidden="true"><span>↗</span></div>;
}

function HeroNetwork() {
  return (
    <div className="hero-network" aria-hidden="true">
      <svg className="network-lines" viewBox="0 0 900 330" fill="none" preserveAspectRatio="none">
        <path d="M0 53C145 53 190 98 300 165" />
        <path d="M0 165H300" />
        <path d="M0 277C145 277 190 232 300 165" />
        <path d="M900 53C755 53 710 98 600 165" />
        <path d="M900 165H600" />
        <path d="M900 277C755 277 710 232 600 165" />
        <circle cx="300" cy="165" r="4" />
        <circle cx="600" cy="165" r="4" />
      </svg>
      <span className="network-badge badge-left-top">RGB</span>
      <span className="network-badge badge-left-mid">GIS</span>
      <span className="network-badge badge-left-bottom">DSM</span>
      <span className="network-badge badge-right-top">AI</span>
      <span className="network-badge badge-right-mid">3D</span>
      <span className="network-badge badge-right-bottom">MAP</span>
      <div className="network-core"><span>AI</span></div>
    </div>
  );
}

function App() {
  const [activeNav, setActiveNav] = useState<NavItem>("New reconstruction");
  const [activeReferenceNav, setActiveReferenceNav] = useState<ReferenceNavItem>("Home");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [backendStatus, setBackendStatus] = useState<"checking" | "online" | "offline">("checking");
  const [predictionState, setPredictionState] = useState<PredictionState>("idle");
  const [prediction, setPrediction] = useState<PredictionResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [layers, setLayers] = useState<SceneLayers>(DEFAULT_SCENE_LAYERS);
  const [benchmarks, setBenchmarks] = useState<BenchmarkResult[]>([]);
  const [benchmarkState, setBenchmarkState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const uploadSectionRef = useRef<HTMLDivElement>(null);

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
    void startPrediction(file);
  }

  function focusReconstruction() {
    setActiveNav("New reconstruction");
    setActiveReferenceNav("Home");
    setPrediction(null);
    setPredictionState("idle");
    setSelectedFile(null);
    setErrorMessage(null);
    window.requestAnimationFrame(() => {
      uploadSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
      uploadSectionRef.current?.querySelector<HTMLButtonElement>("button")?.focus();
    });
  }

  function selectReferenceNav(item: ReferenceNavItem) {
    setActiveReferenceNav(item);
    if (item === "Home" || item === "Products") {
      setActiveNav("New reconstruction");
      window.requestAnimationFrame(() => uploadSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "center" }));
    } else if (item === "Resources") {
      setActiveNav("Examples");
    } else {
      setActiveNav("About");
    }
  }

  async function startPrediction(file?: File, exampleId?: string) {
    setPredictionState("processing");
    setPrediction(null);
    setErrorMessage(null);
    const formData = new FormData();
    if (file) formData.append("file", file);
    if (exampleId) formData.append("example_id", exampleId);

    try {
      const response = await fetch("http://localhost:8000/api/predict", { method: "POST", body: formData });
      const body = await response.json() as PredictionResult | { detail?: string };
      if (!response.ok) throw new Error("detail" in body ? body.detail : "Prediction could not be created.");
      setPrediction(body as PredictionResult);
      setLayers(DEFAULT_SCENE_LAYERS);
      setSelectedFile(file ?? null);
      setPredictionState("success");
    } catch (error) {
      setPredictionState("error");
      setErrorMessage(error instanceof Error ? error.message : "Prediction could not be created.");
    }
  }

  return (
    <main className="page-shell">
      <section className="app-window" aria-label="DepthWizard workspace">
        <header className="reference-navbar">
          <button className="brand-lockup" onClick={() => selectReferenceNav("Home")} aria-label="DepthWizard home">
            <BrandMark />
            <span className="brand-name">DepthWizard</span>
          </button>
          <nav className="reference-navigation" aria-label="Main navigation">
            {(["Home", "Products", "Industries", "Company", "Resources"] as ReferenceNavItem[]).map((item) => (
              <button key={item} className={activeReferenceNav === item ? "active" : ""} onClick={() => selectReferenceNav(item)}>{item}</button>
            ))}
          </nav>
          <button className="nav-cta" onClick={focusReconstruction}>New reconstruction <span>→</span></button>
        </header>

        <div className="workspace">
          <div className="workspace-content">
            {activeNav === "New reconstruction" && predictionState === "success" && prediction ? (
              <section className="result-card">
                <div className="result-heading">
                  <div>
                    <p className="eyebrow">Interactive reconstruction</p>
                    <h2>{prediction.sourceName}</h2>
                  </div>
                  <div className="result-badge"><span className="status-dot online" /> {prediction.isFixture ? "Fixture result" : "Live model result"}</div>
                </div>
                <div className="result-body">
                  <ReconstructionViewer
                    heightData={prediction.heightData}
                    gridSize={prediction.gridSize}
                    maxHeight={prediction.maxHeight}
                    buildingRegions={prediction.buildingRegions}
                    semanticData={prediction.semanticData}
                    semanticGridSize={prediction.semanticGridSize}
                    layers={layers}
                    inputImageUrl={`http://localhost:8000${prediction.inputImageUrl}`}
                  />
                  <PredictionInspector prediction={prediction} layers={layers} onToggleLayer={(layer) => setLayers((current) => ({ ...current, [layer]: !current[layer] }))} />
                </div>
                <div className="result-footer">
                  <span>{prediction.heightReference === "absolute" ? "Metric DSM · meters" : "Estimated nDSM · relative meters"}</span>
                  <span>{prediction.width} × {prediction.height} input · {prediction.gridSize} × {prediction.gridSize} scene</span>
                  <button className="text-button" onClick={focusReconstruction}>New reconstruction <span>→</span></button>
                </div>
              </section>
            ) : activeNav === "New reconstruction" && (
              <section className="home-view">
                <div className="hero-copy">
                  <div className="integration-pill"><span className={`pill-dot ${backendStatus}`} /> Aerial imagery to interactive 3D <span className="integration-separator">·</span> GAMUS</div>
                  <h1>Turn aerial imagery into an explorable 3D world</h1>
                  <p>DepthWizard transforms RGB imagery and geospatial signals into estimated height models and stylized scenes you can understand at a glance.</p>
                  <button className="primary-button hero-button" onClick={() => fileInputRef.current?.click()}>Start a reconstruction <span>→</span></button>
                </div>
                <HeroNetwork />
                <div
                  ref={uploadSectionRef}
                  className={`upload-card ${isDragging ? "dragging" : ""}`}
                onDragEnter={(event) => { event.preventDefault(); setIsDragging(true); }}
                onDragOver={(event) => event.preventDefault()}
                onDragLeave={() => setIsDragging(false)}
                onDrop={(event) => { event.preventDefault(); setIsDragging(false); handleFile(event.dataTransfer.files[0]); }}
                aria-label="Upload aerial image"
              >
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
                  <button className="primary-button" onClick={() => fileInputRef.current?.click()}>
                    <Icon name="plus" /> Upload aerial image
                  </button>
                </>}
                <input ref={fileInputRef} className="visually-hidden" type="file" accept={ACCEPTED_FORMATS} onChange={(event) => handleFile(event.target.files?.[0])} />
                <div className="supported-formats"><span>PNG</span><span>JPEG</span><span>RGB GeoTIFF</span></div>
                <button className="text-button" onClick={() => void startPrediction(undefined, "gamus-urban-demo")}>Try a GAMUS example <span>→</span></button>
                </div>
              </section>
            )}

            {activeNav === "Examples" && (benchmarkState === "ready" && benchmarks.length ? <BenchmarkWorkspace benchmarks={benchmarks} /> : <section className="empty-panel"><div className="panel-icon"><Icon name="layers" /></div><h2>{benchmarkState === "error" ? "Benchmark unavailable" : "Loading benchmark examples"}</h2><p>{benchmarkState === "error" ? "Start the backend and try again to load reference comparisons." : "Preparing input, reference, prediction, error map, and accuracy metrics."}</p>{benchmarkState === "error" && <button className="primary-button" onClick={() => setBenchmarkState("idle")}>Try again</button>}</section>)}
            {activeNav === "About" && <section className="about-panel" aria-label="About DepthWizard">
              <div className="about-intro">
                <div className="panel-icon"><Icon name="book" /></div>
                <p className="eyebrow">The DepthWizard approach</p>
                <h2>From one aerial image to a clearer view of the world.</h2>
                <p>DepthWizard turns RGB imagery into estimated height-above-ground models and explorable stylized scenes. It is built to make model output legible without presenting a prediction as a survey.</p>
              </div>
              <div className="about-grid">
                <article className="about-card about-card-accent"><span className="about-card-kicker">Model</span><h3>DepthAnything V2</h3><p>A fine-tuned small model produces non-negative estimated nDSM values in meters for supported aerial imagery.</p></article>
                <article className="about-card"><span className="about-card-kicker">Training context</span><h3>GAMUS urban data</h3><p>The model is tuned around GAMUS imagery, so dense urban scenes are its clearest expected use case.</p></article>
                <article className="about-card"><span className="about-card-kicker">Scientific honesty</span><h3>Estimated, not absolute</h3><p>Arbitrary uploads show diagnostics and height ranges. Accuracy metrics appear only when a reference-backed benchmark is available.</p></article>
              </div>
              <div className="about-note"><span className="pill-dot online" /> Forested scenes may represent canopy height more reliably than bare-ground elevation from a single RGB image.</div>
            </section>}
          </div>
        </div>
      </section>
    </main>
  );
}

export { App };
