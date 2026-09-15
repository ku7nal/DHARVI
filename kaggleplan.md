  # Kaggle Notebook Implementation Plan

  The notebook will be delivered as copy-pasteable cells, using the complete GAMUS dataset for a short full-data smoke test
  before final training.

  The implementation will match the hackathon repository’s requirements for relative nDSM, calibrated GeoTIFF DSM, metrics,
  semantic output, and Three.js integration. SIH DepthWizard repository

  ## Notebook Blocks

  ### Block 1 — Install dependencies

  Install:

  h5py
  rasterio
  albumentations
  opencv-python-headless
  scikit-learn
  scipy
  pandas
  matplotlib
  seaborn
  tqdm

  ### Block 2 — Configure paths

  Set:

  GAMUS_ROOT = "/kaggle/input/your-full-gamus-dataset"
  WORK_ROOT = "/kaggle/working/depthwizard_final"

  The notebook will never write to /kaggle/input. Any generated script or checkpoint will be written to /kaggle/working.

  ### Block 3 — Verify the complete dataset

  The cell will:

  - Discover images, heights, and classes
  - Count all train/validation/test samples
  - Pair files by tile ID
  - Verify HDF5 keys
  - Verify spatial dimensions
  - Verify class IDs 0..6
  - Print whether the dataset is full GAMUS or a subset

  It will stop if files are missing or mismatched.

  ### Block 4 — Generate the dataset manifest

  Save:

  gamus_manifest.json
  dataset_audit.json
  class_histogram.png
  height_distribution.png

  The manifest will record:

  - dataset revision
  - sample counts
  - HDF5 keys
  - height statistics
  - class statistics
  - invalid pixel counts
  - city/source groups
  - dataset completeness

  ### Block 5 — Inspect samples visually

  Display:

  RGB
  reference height
  semantic mask
  building mask
  validity mask

  The cell will verify:

  class 3 = building
  class 4 = water
  class 5 = road
  class 6 = tree

  ### Block 6 — Define the native crop dataset

  Use native 518×518 crops instead of resizing complete 1024×1024 images.

  Crop sampling:

  50% uniform
  25% building-rich
  15% high-height
  10% boundary-rich

  All transformations must be applied consistently to RGB, height, semantic, validity, and boundary targets.

  ### Block 7 — Define augmentations

  Use:

  - horizontal flip
  - vertical flip
  - 90-degree rotations
  - mild square crop scale
  - brightness/contrast changes
  - mild saturation/hue variation
  - gamma variation
  - small Gaussian noise
  - mild blur
  - mild JPEG compression

  Do not use:

  - perspective warps
  - elastic deformation
  - vertical height scaling
  - MixUp
  - CutMix

  ### Block 8 — Define the final model

  Use:

  Depth Anything V2 Base
  + multi-scale DPT decoder
  + height head
  + seven-class semantic head
  + building-boundary head

  The implementation will use intermediate feature levels instead of only the final hidden state. Depth Anything V2 is
  designed around DINOv2 features and DPT decoding. Depth Anything V2 documentation

  ### Block 9 — Define the loss

  Use:

  weighted Smooth L1 height loss
  + height-gradient loss
  + log-height loss
  + class-balanced semantic cross entropy
  + Dice loss
  + building-boundary BCE loss

  Height remains the primary objective.

  ### Block 10 — Run a one-batch test

  Verify:

  - model loads
  - forward pass works
  - loss is finite
  - backward pass works
  - gradients are finite
  - outputs have correct dimensions
  - predictions are non-constant
  - semantic IDs are valid

  ### Block 11 — Run a four-tile overfit test

  Train temporarily on four complete tiles.

  The test must confirm that:

  - training loss decreases
  - buildings appear in the semantic output
  - predicted heights vary spatially
  - checkpoint save/reload works

  ### Block 12 — Run the full-data smoke test

  Use every available GAMUS sample but only two epochs:

  model: Depth Anything V2 Base
  image size: 518
  batch size: 2
  gradient accumulation: 4
  epochs: 2
  full train split
  full validation split
  full test split

  This smoke test must use the same final architecture, augmentations, losses, tiling, and metrics as the final training
  run.

  Output:

  /kaggle/working/depthwizard_smoke_full/

  ### Block 13 — Full-image tiled inference

  Use:

  tile size: 518
  overlap: 50%
  reflection padding
  Hann-window blending
  horizontal-flip TTA

  Evaluate complete validation and test images rather than only random crops.

  ### Block 14 — Calculate final metrics

  Calculate:

  RMSE
  MAE
  Pearson correlation

  Report:

  - pooled pixel metrics
  - macro per-tile metrics
  - 95% bootstrap confidence intervals
  - height-range metrics
  - building metrics
  - tall-structure metrics
  - per-city/source metrics
  - semantic mIoU
  - per-class IoU
  - building IoU
  - boundary F1

  Checkpoint selection will use:

  lowest macro validation RMSE
  then lowest MAE
  then highest correlation

  ### Block 15 — Generate visual reports

  Save comparison panels containing:

  RGB
  reference height
  predicted height
  absolute error
  reference semantic mask
  predicted semantic mask
  building boundary

  ### Block 16 — Reload the checkpoint

  Load the saved checkpoint again using the exact production inference wrapper.

  Verify:

  - checkpoint loads
  - inference output matches the training evaluator
  - semantic output has seven channels
  - output dimensions match the original image

  ### Block 17 — Export dinosaur.pth

  Export:

  dinosaur.pth
  model_config.json
  metrics.json
  metrics_by_tile.jsonl
  gamus_manifest.json
  visual_report/

  The checkpoint will include:

  - model ID
  - class names
  - class count
  - building class
  - normalization
  - height scale
  - crop size
  - tile overlap
  - dataset revision
  - training configuration
  - validation metrics
  - test metrics
  - checkpoint format version

  ### Block 18 — Final full training command

  After the smoke test passes, reuse the same notebook and change only:

  EPOCHS = 50
  OUTPUT_DIR = "/kaggle/working/depthwizard_final"

  The full training will use:

  AdamW
  encoder LR: 1e-5
  decoder/head LR: 1e-4
  weight decay: 1e-4
  cosine schedule
  5% warmup
  EMA weights
  gradient accumulation
  early stopping

  ### Block 19 — Backend integration verification

  The final cells will verify compatibility with:

  backend/app/model_service.py
  backend/app/main.py
  backend/app/geospatial.py
  frontend/src/semanticTerrain.ts
  frontend/src/scene/ReconstructionViewer.tsx

  The backend must be updated to load the new multiscale checkpoint format rather than assuming the old base.* model
  structure.

  ### Block 20 — Renderer verification

  The output must:

  - extract building regions before semantic downsampling
  - preserve small building footprints
  - preserve roof-height variation
  - limit tree instances
  - keep trees disabled by default
  - avoid one mesh per tree pixel
  - preserve roads and water visually
  - retain height detail for buildings

  ## Smoke-Test Acceptance Criteria

  The full-data two-epoch smoke test passes only if:

  - Every available sample is read successfully.
  - No HDF5 pairing errors occur.
  - No CUDA device-side assertions occur.
  - Losses are finite.
  - Full validation and test inference complete.
  - Metrics are generated.
  - The checkpoint reloads.
  - Semantic IDs remain 0..6.
  - Height predictions are non-constant.
  - Visual reports are created.
  - The backend wrapper can load the checkpoint.

  The smoke-test checkpoint will not be used as the final production model.
