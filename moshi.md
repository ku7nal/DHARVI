# DepthWizard — Complete Technical Project Brief

## 1. Executive summary

DepthWizard converts one aerial RGB image into an estimated height-above-ground map and an interactive 3D terrain scene.

It supports two input modes:

| Input | Output | Meaning |
|---|---|---|
| PNG/JPG | Relative DSM / estimated nDSM | Relative or locally estimated structure height |
| GeoTIFF | Calibrated metric DSM | Metric elevation when DEM or GCP evidence is available |

The model predicts height above local ground. Absolute elevation is produced only after a geospatial calibration stage. A CRS alone does not tell the model how high a building is above sea level.

The project combines:

- pretrained monocular depth estimation;
- remote-sensing nDSM supervision;
- semantic segmentation;
- building-boundary prediction;
- geospatial DEM/GCP calibration;
- procedural 3D geometry;
- browser-based WebGL visualization.

---

## 2. Problem and motivation

LiDAR, stereo imaging, and InSAR can produce high-quality elevation products, but they can be expensive, sensor-dependent, and computationally heavy. A single-view RGB solution is easier to deploy, but generic depth models are trained primarily on natural ground-level imagery.

Remote-sensing imagery creates a domain gap because it contains:

- top-down viewpoints;
- roofs, roads, and terrain instead of camera-level objects;
- repeated urban structures;
- shadows and occlusions;
- trees and canopy surfaces;
- different spatial scales;
- no direct absolute scale in the RGB image.

DepthWizard adapts a pretrained model to aerial imagery using GAMUS aligned RGB, normalized surface height, and semantic labels.

---

## 3. End-to-end architecture

```text
RGB image / GeoTIFF
        |
        v
Input validation and metadata extraction
        |
        v
Overlapping 518 x 518 image tiles
        |
        v
Depth Anything V2 Base
        |
        +------------------+-------------------+
        |                  |                   |
        v                  v                   v
   Height head       Semantic head      Boundary head
        |                  |                   |
        +------------------+-------------------+
                           |
                           v
          nDSM + semantic layers + boundaries
                           |
              DEM/GCP calibration when possible
                           |
                           v
              Terrain and building mesh generation
                           |
                           v
                    Interactive Three.js scene
```

The backend is FastAPI/Python. The frontend is React/TypeScript with Three.js. The model is PyTorch with Hugging Face Transformers.

---

## 4. GAMUS dataset

GAMUS contains co-registered remote-sensing RGB imagery, nDSM/AGL height data, and semantic labels.

The semantic taxonomy is:

| ID | Class |
|---:|---|
| 0 | others/background |
| 1 | ground |
| 2 | low vegetation |
| 3 | building |
| 4 | water |
| 5 | road |
| 6 | tree |

The Hugging Face release is split into separate modality directories. The observed layout is:

```text
images/train/DC_01_25_RGB.h5
heights/train/DC_01_25_AGL.h5
classes/train/DC_01_25_CLS.h5
```

The shared ID `DC_01_25` defines one aligned training example:

```text
RGB image + AGL/nDSM height + semantic class mask
```

The generic call `load_dataset("earthflow/GAMUS", streaming=True)` is not sufficient for this task. It exposes one `image` feature and treats RGB, height, and class files as separate examples. The observed values `1, 2, 3, 5, 6` were semantic class IDs, not RGB pixels.

The loader must pair files by shared ID after removing:

```text
_RGB, _AGL, _CLS
```

References:

- [GAMUS Hugging Face dataset](https://huggingface.co/datasets/earthflow/GAMUS)
- [Official GAMUS repository and loader](https://github.com/EarthNets/RSI-MMSegmentation)
- [GAMUS paper](https://arxiv.org/abs/2305.14914)

---

## 5. Remote dataset ingestion on Kaggle

The complete dataset should not be downloaded to the developer’s computer or copied into Kaggle’s `/kaggle/working` directory.

The intended flow is:

```text
Hugging Face remote files
        |
        | one RGB/AGL/CLS triplet at a time
        v
Kaggle temporary memory/cache
        |
        v
PyTorch crop and training batch
```

The remote loader should:

1. list the `images`, `heights`, and `classes` directories;
2. list files for `train`, `validation`, and `test`;
3. normalize filenames to shared sample IDs;
4. reject missing, duplicate, or ambiguous modality files;
5. fetch only the current triplet;
6. read the HDF5 arrays;
7. create a crop and release the raw arrays;
8. save only the manifest, checkpoints, metrics, and visual examples.

The Kaggle workspace should contain only small artifacts:

```text
/kaggle/working/
  gamus_manifest.json
  checkpoint_epoch_*.pth
  best_model.pth
  metrics.json
  validation_examples/
```

The dataset itself remains remote or in read-only input storage. The exact Hugging Face revision must be recorded because releases differ in size and layout.

---

## 6. Dataset audit

Before model construction, the audit produces `gamus_manifest.json`.

It records:

- dataset ID and exact revision;
- split names and sample counts;
- RGB/height/class file paths or remote IDs;
- HDF5 keys;
- shapes and dtypes;
- finite and invalid height-pixel counts;
- semantic IDs and class frequencies;
- height min/max/percentiles;
- source or city group;
- building-pixel fraction.

The audit fails visibly on:

- missing modalities;
- duplicate IDs;
- corrupt HDF5 files;
- ambiguous HDF5 keys;
- RGB/height/class shape mismatch;
- invalid semantic IDs outside `0..6`;
- empty splits;
- silently omitted files.

The current repository already contains a local-directory audit utility. The remote version must use the same manifest contract while reading `_RGB`, `_AGL`, and `_CLS` files from Hugging Face one triplet at a time.

---

## 7. Model architecture

### 7.1 Depth Anything V2 Base backbone

The main backbone is Depth Anything V2 Base. It is a pretrained vision-transformer-based monocular depth model, not a conventional CNN-only model.

The pretrained backbone provides useful features for:

- edges;
- textures;
- surfaces;
- object boundaries;
- global scene structure;
- relative depth ordering.

Fine-tuning adapts those features from natural imagery to aerial remote sensing.

Reference: [Depth Anything V2](https://github.com/DepthAnything/Depth-Anything-V2)

### 7.2 Height head

The height path predicts one continuous value per pixel:

```text
RGB tile → backbone features → height decoder → H x W nDSM map
```

The output is constrained to be non-negative. Its supervision is the GAMUS AGL/nDSM raster, so the network learns height above local ground rather than camera distance.

### 7.3 Semantic head

The semantic head is a small CNN dense-prediction head attached to backbone features:

```text
features → 3x3 convolution → GELU → 1x1 convolution → 7 class logits
```

It predicts the seven GAMUS classes and helps separate buildings from roads, vegetation, trees, water, and ground.

### 7.4 Building-boundary head

The boundary head is another small CNN head:

```text
features → 3x3 convolution → GELU → 1x1 convolution → boundary logits
```

Its target is derived from the building mask. It encourages sharp building footprints and roof transitions.

### 7.5 Why multitask learning

Height-only prediction can mistake a tree, shadow, terrain ridge, or dark road for a building. Semantic and boundary supervision provides additional structural constraints. Height remains the primary task, so the model is selected by height accuracy rather than segmentation accuracy alone.

The current `dinosaur.pth` and `billi.pth` checkpoints are Base height-only checkpoints. The final checkpoint should produce height, semantic, and boundary outputs.

---

## 8. Input preparation and training crops

Do not resize an entire large GAMUS tile directly into 518×518 because small buildings and roof boundaries disappear. Read the original RGB, AGL, and semantic arrays, select a 518×518 crop, and apply exactly the same crop and geometric transform to every modality.

Use random horizontal and vertical flips, random 90-degree rotations, and mild brightness, contrast, and color changes. Never apply independent geometric transforms to RGB and targets.

The validity mask is `finite(height) AND class_id in {0,1,2,3,4,5,6}`. Invalid pixels contribute zero loss and remain visible in the audit report.

---

## 9. Training losses

The height objective remains primary. The proposed objective is:

- `1.00 × masked height Huber loss`;
- `0.15 × masked log-height Huber loss`;
- `0.10 × height-gradient loss`;
- `0.15 × class-balanced semantic loss`;
- `0.05 × building-boundary loss`.

Huber loss is robust to unusual outliers such as antennas, poles, and corrupted pixels. The height loss is calculated only on valid pixels.

Ground pixels are abundant and tall structures are rare, so use bounded target-dependent weighting: `clamp(1 + 1.5 × building_mask + normalized_target_height, 1, 4)`. The weight must depend only on the target, never on the model’s current error. A previous self-normalized loss made training loss look stable while RMSE stayed poor.

The gradient term compares local horizontal and vertical height changes and helps preserve roof edges. Semantic training uses class-balanced cross-entropy. The boundary head uses binary cross-entropy with logits.

---

## 10. Kaggle training protocol

### Stage A — height warm-up

Load pretrained Depth Anything V2 Base, initialize the height head, freeze the encoder for 1–2 epochs, train the height path, and then unfreeze the encoder.

### Stage B — height fine-tuning

Use AdamW, `1e-5` backbone learning rate, `1e-4` task-head learning rate, `1e-4` weight decay, mixed precision, gradient clipping at `1.0`, and gradient accumulation.

### Stage C — multitask fine-tuning

Train height, semantics, and boundaries jointly. Select the best checkpoint by complete-image validation RMSE, with MAE and correlation as supporting metrics.

Suggested limits are 30 maximum epochs, six unimproved validation evaluations for early stopping, effective batch size approximately 8–16, and 518×518 crops.

T4 memory may require a small physical batch plus gradient accumulation. Save a checkpoint after every epoch so a Kaggle session interruption does not destroy progress.

Each checkpoint should include model, optimizer, scheduler, scaler, epoch, model ID, image size, normalization, semantic taxonomy, dataset revision, manifest hash, configuration, and validation metrics.

---

## 11. Required experiments

### Remote ingestion smoke test

Read several aligned triplets from every split. Verify RGB range, height range, semantic IDs, dimensions, and filename pairing.

### Training smoke test

Use 100–300 examples for 1–2 epochs. Verify loading, forward pass, backward pass, mixed precision, checkpoint resume, tiled validation, non-constant predictions, and no all-ground collapse.

### Model pilot

Compare Depth Anything V2 Small and Base with identical crops, losses, augmentations, and validation. Choose Base when it gives a meaningful height improvement and fits Kaggle reliably.

### Complete training

Train every official training sample. Use validation for selection and keep the official test split untouched until final reporting.

---

## 12. Validation metrics

Height metrics are RMSE, MAE, Pearson correlation, ground-only error, non-ground error, building-only error, and tall-structure error.

Semantic metrics are mean IoU, per-class IoU, building IoU, building precision/recall/F1, and building-boundary F1.

Break results down by city/source group, height range, building density, and valid-pixel status. GAMUS is urban-focused, so sparse, hilly, and forested claims require separate labelled external data. Synthetic fixtures are for UI testing, not measured field validation.

Every validation montage should show RGB, reference nDSM, prediction, absolute error, semantics, boundary prediction, and the 3D scene.

---

## 13. Production inference

For arbitrary-size input, convert to RGB, divide into overlapping 518×518 tiles, reflection-pad edge tiles, apply training normalization, predict each tile, run horizontal-flip test-time augmentation, blend overlaps with a smooth window, reconstruct the full-resolution height map, retain semantic/boundary predictions, and send the result to scene generation.

This prevents visible tile seams. The backend loads the checkpoint once at startup and rejects incompatible taxonomy or missing metadata.

---

## 14. Non-georeferenced PNG/JPG path

PNG/JPG follows: RGB preprocessing → model inference → estimated nDSM → relative 3D terrain scene.

The result is labelled `Estimated relative nDSM`. A PNG/JPG has no reliable coordinate system, ground elevation, or vertical datum.

---

## 15. GeoTIFF and metric DSM path

For GeoTIFF input, preserve CRS, affine transform, bounds, resolution, dimensions, nodata values, and source-band metadata.

The calibrated product is `absolute DSM = predicted nDSM + calibrated ground elevation`.

Ground elevation can come from SRTM, a lower-resolution DEM, a DTM, or Ground Control Points. When GCPs exist, fit a robust correction such as `corrected height = scale × predicted nDSM + offset + ground elevation`.

Report calibration method, number and coverage of control points, residual error, and confidence. Without CRS or valid ground evidence, return a non-metric status instead of claiming an absolute DSM. Successful output is a float32 GeoTIFF preserving the source spatial reference.

---

## 16. Interactive 3D visualization

The predicted height raster becomes a grid mesh: pixel grid → vertices `(x, y, height)` → triangles → terrain surface. The original RGB image becomes the terrain texture.

Semantic predictions control the scene: ground becomes the terrain base, buildings become footprints and roofs, roads become road layers, water becomes a water material, low vegetation becomes vegetation, and trees become bounded canopy objects.

Building extraction happens before coarse terrain reduction. Connected building regions are cleaned, local ground height is estimated, walls are generated, flat or gabled roofs are inferred from local height variation, and RGB texture is projected onto the geometry. Distant buildings use lower-detail geometry for browser performance.

The viewer supports first-person navigation, orbit/flythrough controls, height inspection, slope view, RGB texture view, height-map view, semantic toggles, wireframe mode, and layer visibility controls. Three.js integrates directly with the existing web application without a separate game-engine runtime.

---

## 17. Software architecture

```text
React + TypeScript + Three.js frontend
              |
              v
FastAPI backend
  ├── upload validation
  ├── GeoTIFF reader
  ├── model service
  ├── tiled inference
  ├── DEM/GCP calibration
  ├── GeoTIFF writer
  └── scene response
              |
              v
PyTorch model
  ├── Depth Anything V2 Base
  ├── nDSM height head
  ├── semantic CNN head
  └── boundary CNN head
```

The frontend receives a model-agnostic result contract containing input dimensions, prediction dimensions, height data, semantic data, height reference, units, calibration status, preview URLs, and known limitations.

---

## 18. Why use both transformers and CNNs?

Depth Anything V2 supplies transformer-based global visual features. The task heads use small convolutional layers for efficient local dense prediction. This provides global context, local edge sensitivity, dense pixel-level outputs, and practical inference on Kaggle T4 GPUs. Classical geospatial processing handles calibration and GeoTIFF export; procedural geometry and WebGL handle the interactive scene.

---

## 19. Main technical risks and mitigations

| Risk | Mitigation |
|---|---|
| Generic model predicts relative depth only | Fine-tune on GAMUS nDSM height labels |
| Domain gap from natural images | Use aerial RGB/height supervision and remote-sensing augmentation |
| Ground pixels dominate the loss | Use bounded target-dependent weighting |
| Small buildings disappear | Use native-resolution crops |
| Tile seams appear | Use overlap, smooth blending, and flip TTA |
| Trees are mistaken for buildings | Use semantic and boundary heads |
| Absolute height is falsely claimed | Require DEM/GCP calibration and report confidence |
| Kaggle session ends | Save resumable epoch checkpoints |
| 70 GB exceeds writable workspace | Stream remote files and save only artifacts |
| GAMUS is urban-focused | Report external landscape validation separately |
| Canopy is compared to bare earth | Distinguish DSM/canopy height from DTM elevation |

---

## 22. Current implementation status

### Implemented

- FastAPI backend;
- React/TypeScript frontend;
- Three.js terrain viewer;
- GeoTIFF metadata handling;
- calibration status contract;
- height-only Depth Anything V2 checkpoint loading;
- overlapping tile inference;
- semantic scene contract;
- local GAMUS directory audit utility;
- audit manifest tests;
- building and terrain visualization layers.

### Required for the final model

- remote Hugging Face modality-aware audit;
- streaming `_RGB`/`_AGL`/`_CLS` triplet loader;
- Kaggle smoke test;
- native-resolution complete training;
- final multitask checkpoint;
- official GAMUS test evaluation;
- external sparse/hilly/forested validation;
- final calibrated GeoTIFF demonstration.

### Technical honesty statement

The existing height-only checkpoints predict height but do not provide semantic or boundary outputs. The final production checkpoint should be selected only after complete-GAMUS training, full-image validation, and production inference verification.
