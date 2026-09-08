import { useEffect, useRef, useState } from "react";

type NavItem = "New reconstruction" | "Examples" | "About";
type PredictionState = "idle" | "processing" | "success" | "error";

type PredictionResult = {
  id: string;
  status: "complete";
  inputImageUrl: string;
  heightMapUrl: string;
  width: number;
  height: number;
  predictionWidth: number;
  predictionHeight: number;
  minHeight: number;
  maxHeight: number;
  resultType: "estimated_ndsm";
  heightUnit: "meters";
  sourceName: string;
  isFixture: boolean;
};

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
  return <div className="brand-mark" aria-hidden="true">D</div>;
}

function App() {
  const [activeNav, setActiveNav] = useState<NavItem>("New reconstruction");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [backendStatus, setBackendStatus] = useState<"checking" | "online" | "offline">("checking");
  const [predictionState, setPredictionState] = useState<PredictionState>("idle");
  const [prediction, setPrediction] = useState<PredictionResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
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

  function handleFile(file: File | undefined) {
    if (!file) return;
    setSelectedFile(file);
    void startPrediction(file);
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
      setSelectedFile(file ?? null);
      setPredictionState("success");
    } catch (error) {
      setPredictionState("error");
      setErrorMessage(error instanceof Error ? error.message : "Prediction could not be created.");
    }
  }

  const statusLabel = backendStatus === "online" ? "API connected" : backendStatus === "offline" ? "API offline" : "Checking API";

  return (
    <main className="page-shell">
      <section className="app-window" aria-label="DepthWizard workspace">
        <aside className="sidebar">
          <div className="brand-row">
            <BrandMark />
            <span className="brand-name">DepthWizard</span>
            <button className="icon-button sidebar-collapse" aria-label="Collapse navigation"><Icon name="chevron" /></button>
          </div>

          <nav className="navigation" aria-label="Main navigation">
            <p className="nav-label">Workspace</p>
            <button className={`nav-item ${activeNav === "New reconstruction" ? "active" : ""}`} onClick={() => setActiveNav("New reconstruction")}>
              <Icon name="plus" />
              <span>New reconstruction</span>
            </button>
            <button className={`nav-item ${activeNav === "Examples" ? "active" : ""}`} onClick={() => setActiveNav("Examples")}>
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
          <header className="topbar">
            <div className="breadcrumbs">
              <span>{activeNav}</span>
              <span className="breadcrumb-separator">/</span>
              <strong>{selectedFile?.name ?? "Untitled workspace"}</strong>
            </div>
            <div className="topbar-actions">
              <div className="model-pill"><span className="status-dot online" /> DepthAnything V2 · GAMUS</div>
              <button className="icon-button" aria-label="Search"><Icon name="search" /></button>
              <button className="icon-button" aria-label="Notifications"><Icon name="bell" /></button>
              <button className="avatar-button" aria-label="User profile">K</button>
            </div>
          </header>

          <div className="workspace-content">
            <div className="content-heading">
              <div>
                <p className="eyebrow">Monocular height reconstruction</p>
                <h1>{activeNav === "New reconstruction" ? "New reconstruction" : activeNav}</h1>
              </div>
              <div className="content-meta">Estimated nDSM · meters</div>
            </div>

            {activeNav === "New reconstruction" && (
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
                  <p>Creating a fixture result so the scene workspace can load.</p>
                  <div className="progress-track"><span /></div>
                </> : predictionState === "error" ? <>
                  <h2>We could not process that image</h2>
                  <p className="error-copy">{errorMessage}</p>
                  <button className="primary-button" onClick={() => fileInputRef.current?.click()}><Icon name="plus" /> Try another image</button>
                </> : predictionState === "success" && prediction ? <>
                  <h2>Fixture prediction ready</h2>
                  <p>{prediction.sourceName} is ready to explore as Estimated nDSM.</p>
                  <div className="prediction-previews">
                    <figure><img src={`http://localhost:8000${prediction.inputImageUrl}`} alt="Uploaded aerial image" /><figcaption>Input RGB</figcaption></figure>
                    <figure><img src={`http://localhost:8000${prediction.heightMapUrl}`} alt="Estimated nDSM preview" /><figcaption>Estimated nDSM</figcaption></figure>
                  </div>
                  <button className="primary-button" onClick={() => fileInputRef.current?.click()}><Icon name="plus" /> Choose another image</button>
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
              </section>
            )}

            {activeNav === "Examples" && <section className="empty-panel"><div className="panel-icon"><Icon name="layers" /></div><h2>GAMUS examples</h2><p>Load a prepared urban tile to preview the fixture-backed reconstruction workflow.</p><button className="primary-button" onClick={() => { setActiveNav("New reconstruction"); void startPrediction(undefined, "gamus-urban-demo"); }}>Open urban example <span>→</span></button></section>}
            {activeNav === "About" && <section className="empty-panel"><div className="panel-icon"><Icon name="book" /></div><h2>About DepthWizard</h2><p>Explore estimated height above ground from aerial imagery. The first workspace is designed around a fine-tuned DepthAnything V2 model trained on GAMUS.</p></section>}
          </div>
        </div>
      </section>
    </main>
  );
}

export { App };
