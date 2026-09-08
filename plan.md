# DepthWizard Website Plan

## 1. Current understanding

The website will showcase a fine-tuned **DepthAnything V2 Small** model trained on the GAMUS dataset. The immediate goal is to build the frontend and backend around a stable prediction contract, using mock prediction data first. The trained model will be connected later without requiring a frontend redesign.

The product should be minimal, clean, and focused on turning an input aerial image and predicted height map into an explorable 3D city scene.

## 2. Current model assessment

The current prediction is a promising MVP foundation:

- It captures major building and vegetation masses.
- Large roof structures broadly align with the LiDAR nDSM target.
- It follows the overall height distribution.

The current output is not yet sufficient by itself to reproduce the reference renders because it is:

- Soft around building boundaries.
- Missing crisp roof geometry.
- Over-smoothed on small structures.
- Not separated into buildings, roads, water, vegetation, and terrain.
- A height raster rather than a complete 3D scene.

The model is good enough to drive an interactive prototype. The reference visuals require a geometry-generation and rendering pipeline in addition to the model.

## 3. Target visual direction

The reference style is a clean, stylized 3D city model rather than a single displaced height surface.

The rendering pipeline should eventually be:

```text
RGB image
   ├── height model → height map
   ├── semantic model → building/road/tree/water masks
   └── renderer → stylized 3D city
```

The scene should use:

- Light gray buildings.
- White roads and paths.
- Muted green vegetation.
- Blue water.
- Soft directional lighting.
- Ambient occlusion or contact shadows.
- Orthographic or isometric camera presets.
- Optional original RGB texture for comparison.

## 4. Geometry strategy

### Initial prototype

Start with a height-displaced terrain mesh. This allows the frontend and API to be developed before the model is connected and gives us a working 3D viewer quickly.

### Stylized city renderer

To approach the reference renders:

1. Predict the height map.
2. Generate semantic masks for buildings, roads, vegetation, and water.
3. Clean masks using morphology and connected-component filtering.
4. Convert building masks into polygons.
5. Extrude building polygons according to predicted height.
6. Add simple roof primitives such as flat, stepped, or low-pitched roofs.
7. Render each semantic category with a controlled material palette.

For the first approximation, a building mask can be derived from a height threshold:

```text
building_mask = predicted_height > threshold
```

A separate semantic model or multitask height-plus-segmentation model should replace this heuristic for higher-quality results.

Detailed architectural forms cannot be reliably recovered from a single height raster alone. The renderer should aim for a convincing stylized reconstruction rather than exact building geometry.

## 5. Recommended technology stack

### Frontend

- React
- TypeScript
- Vite
- Three.js
- React Three Fiber
- Drei
- Plain CSS or CSS modules for the UI

React Three Fiber will provide the declarative React integration for Three.js. Drei will provide reusable helpers for controls, cameras, environments, and scene composition.

### Backend

- Python
- FastAPI
- Pydantic
- Pillow
- NumPy
- OpenCV or scikit-image
- Shapely for polygon cleanup and building footprints
- Rasterio when GeoTIFF support is added

### Why this stack

- It keeps the frontend responsive and component-based.
- It is well suited to interactive WebGL scenes.
- It allows model inference to remain in Python.
- It supports mock data now and GPU inference later.
- It avoids committing to a desktop wrapper or heavier game engine before the web experience is proven.

## 6. Proposed repository structure

```text
lluna/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── scene/
│   │   ├── features/
│   │   ├── api/
│   │   └── App.tsx
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── routes/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── fixtures/
│   └── requirements.txt
│
└── README.md
```

## 7. Backend API contract

The frontend should communicate with a stable API rather than directly with model code.

### Prediction endpoint

```http
POST /api/predict
Content-Type: multipart/form-data
```

The initial implementation may return a fixture immediately. Later, this endpoint will call DepthAnything V2 inference.

### Example response

```json
{
  "id": "demo-001",
  "status": "complete",
  "inputImageUrl": "/media/demo-001/input.png",
  "heightMapUrl": "/media/demo-001/height-map.png",
  "sceneUrl": "/media/demo-001/scene.json",
  "width": 512,
  "height": 512,
  "minHeight": 0,
  "maxHeight": 42.7,
  "resultType": "relative"
}
```

### Supporting endpoints

```http
GET /api/health
GET /api/predictions/{id}
```

The response should remain model-agnostic. It should describe the result and asset URLs, not expose inference implementation details.

## 8. Model integration boundary

The model should be isolated behind a prediction service:

```python
class PredictionService:
    def predict(self, image_path: str) -> PredictionResult:
        ...
```

The initial service returns fixture data. The later DepthAnything V2 implementation replaces only this service.

The frontend should not need to know whether a result came from:

- A mock fixture.
- DepthAnything V2.
- A GPU inference server.
- A future segmentation pipeline.

## 9. Initial product experience

The first website version should include:

1. A minimal upload landing page.
2. An example/demo scene using fixture data.
3. RGB and height-map previews.
4. An “Explore 3D” action.
5. An interactive 3D viewer with orbit controls.
6. Layer toggles for:
   - RGB image.
   - Height surface.
   - Stylized city.
   - Wireframe.
7. A compact metadata panel showing dimensions, height range, and processing status.

The visual language should be restrained: neutral background, clear typography, low visual noise, and the 3D scene as the main focus.

## 10. Phased implementation plan

### Phase 1 — Project foundation

- Create the frontend and backend directories.
- Add the Vite React TypeScript app.
- Add the FastAPI app.
- Add health-check and static/media handling.
- Establish environment configuration and local development commands.

### Phase 2 — Mock prediction flow

- Add a demo fixture based on the current sample output.
- Implement `POST /api/predict` with a mock response.
- Display uploaded input and predicted height-map assets.
- Add loading, success, and error states.

### Phase 3 — Initial 3D viewer

- Build the height-displaced terrain mesh.
- Add orbit controls and camera reset.
- Add clean lighting and materials.
- Add height-map, RGB, wireframe, and terrain layer modes.

### Phase 4 — Stylized city geometry

- Add building-mask generation.
- Extract and clean building footprints.
- Extrude building polygons from height values.
- Add semantic materials and simple roof treatments.
- Add lighting and camera presets matching the reference style.

### Phase 5 — Real model integration

- Load the fine-tuned DepthAnything V2 Small checkpoint in the backend.
- Match preprocessing to the training pipeline.
- Return the real prediction assets through the existing API contract.
- Verify output dimensions, normalization, and height ranges.

### Phase 6 — Quality and validation

- Add prediction caching.
- Improve large-image handling.
- Add metrics and comparison views where reference data is available.
- Add GeoTIFF metadata and SRTM support later if required.
- Test WebGL performance on the intended demo machine.

## 11. Important limitations

- A height map alone cannot reproduce exact architectural detail.
- Height-threshold building masks will be approximate.
- GAMUS is primarily US urban data, so generalization outside that domain should be reported honestly.
- Forested areas represent canopy height more reliably than bare-ground elevation.
- Absolute elevation accuracy will depend on the quality of the elevation reference used later.

## 12. Immediate next step

Build the frontend/backend skeleton and mock prediction flow first. Use the current sample image and prediction as fixture assets. Once the upload-to-viewer experience works, add the height-displaced terrain renderer, then replace the fixture prediction service with the fine-tuned DepthAnything V2 model.
