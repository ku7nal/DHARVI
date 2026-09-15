# Kaggle final GAMUS training cells

These cells run the full attached GAMUS split for a two-epoch smoke test. The
same command can then be rerun without `--smoke-test` for final training.

Upload these files to the Kaggle notebook session first:

- `backend/training/kaggle_final_train.py`
- `backend/training/depthwizard_model.py`

Do not write into `/kaggle/input`; generated files belong in `/kaggle/working`.

## Cell 1 — Install dependencies

```python
!pip install -q "transformers>=4.45,<5" accelerate h5py rasterio albumentations scikit-learn scipy pandas matplotlib seaborn tqdm
```

## Cell 2 — Copy the trainer files

Change `CODE_ROOT` to the Kaggle Dataset containing the two Python files.

```python
from pathlib import Path
import shutil

CODE_ROOT = Path("/kaggle/input/your-code-dataset")
WORK_ROOT = Path("/kaggle/working/depthwizard_src")
WORK_ROOT.mkdir(parents=True, exist_ok=True)

for filename in ("kaggle_final_train.py", "depthwizard_model.py"):
    source = CODE_ROOT / filename
    if not source.exists():
        raise FileNotFoundError(source)
    shutil.copy2(source, WORK_ROOT / filename)

print(list(WORK_ROOT.iterdir()))
```

## Cell 3 — Install the Hugging Face downloader

```python
!pip install -q huggingface_hub
```

## Cell 4 — Download GAMUS from Hugging Face

The complete Hugging Face release is approximately 80 GB. Standard Kaggle
sessions often do not have enough free disk, so this cell stops before starting
a partial download.

```python
import os
import shutil
from pathlib import Path
from huggingface_hub import HfApi, snapshot_download

HF_DATASET_ID = "earthflow/GAMUS"
HF_TOKEN = os.environ.get("HF_TOKEN") or None
DOWNLOAD_ROOT = Path("/kaggle/working/hf_gamus")

free_bytes = shutil.disk_usage("/kaggle/working").free
required_bytes = 85 * 1024**3
if free_bytes < required_bytes:
    raise RuntimeError(
        f"Only {free_bytes / 1024**3:.1f} GB are free, but full GAMUS needs about "
        f"{required_bytes / 1024**3:.0f} GB. Attach a Kaggle Dataset containing "
        "GAMUS or use the 5GB subset instead."
    )

revision = HfApi(token=HF_TOKEN).dataset_info(HF_DATASET_ID, revision="main").sha
print("Pinned GAMUS revision:", revision)

downloaded = Path(snapshot_download(
    repo_id=HF_DATASET_ID,
    repo_type="dataset",
    revision=revision,
    local_dir=DOWNLOAD_ROOT,
    token=HF_TOKEN,
    max_workers=8,
    allow_patterns=["**/*.h5", "**/*.hdf5"],
))

roots = [
    path.parent.parent
    for path in downloaded.rglob("images/train")
    if (path.parent.parent / "heights" / "train").is_dir()
    and (path.parent.parent / "classes" / "train").is_dir()
]
if not roots and (downloaded / "images" / "train").is_dir():
    roots = [downloaded]
if not roots:
    raise FileNotFoundError(f"GAMUS layout not found below {downloaded}")

GAMUS_ROOT = roots[0]
DATASET_ID = HF_DATASET_ID
DATASET_REVISION = revision
print("GAMUS_ROOT:", GAMUS_ROOT)
print("Free disk remaining:", shutil.disk_usage("/kaggle/working").free / 1024**3, "GB")
```

## Cell 5 — Full-data smoke test

This uses every available train, validation, and test sample. Only the epoch
count and crops-per-sample are reduced.

```python
import subprocess

subprocess.run([
    "python", str(WORK_ROOT / "kaggle_final_train.py"),
    "--root", str(GAMUS_ROOT),
    "--output-dir", "/kaggle/working/depthwizard_smoke_full",
    "--dataset-id", DATASET_ID,
    "--dataset-revision", DATASET_REVISION,
    "--image-key", "image",
    "--height-key", "image",
    "--class-key", "image",
    "--model-id", "depth-anything/Depth-Anything-V2-Base-hf",
    "--crop-size", "518",
    "--batch-size", "2",
    "--accumulation", "4",
    "--num-workers", "2",
    "--smoke-test",
], check=True)
```

## Cell 6 — Inspect smoke-test metrics

```python
import json
from pathlib import Path

smoke_dir = Path("/kaggle/working/depthwizard_smoke_full")
metrics = json.loads((smoke_dir / "metrics.json").read_text())
print(json.dumps({
    "samples": {
        "train": metrics["train_samples"],
        "validation": metrics["validation_samples"],
        "test": metrics["test_samples"],
    },
    "validation": metrics["validation"],
    "test": metrics["test"],
}, indent=2))
```

## Cell 7 — Full final training

Run this only after the full-data smoke test completes successfully.

```python
subprocess.run([
    "python", str(WORK_ROOT / "kaggle_final_train.py"),
    "--root", str(GAMUS_ROOT),
    "--output-dir", "/kaggle/working/depthwizard_final",
    "--dataset-id", DATASET_ID,
    "--dataset-revision", DATASET_REVISION,
    "--image-key", "image",
    "--height-key", "image",
    "--class-key", "image",
    "--model-id", "depth-anything/Depth-Anything-V2-Base-hf",
    "--crop-size", "518",
    "--batch-size", "2",
    "--accumulation", "4",
    "--num-workers", "2",
    "--epochs", "50",
    "--crops-per-sample", "4",
], check=True)
```

## Cell 8 — Copy the production checkpoint

```python
from pathlib import Path
import shutil

checkpoint = Path("/kaggle/working/depthwizard_final/dinosaur.pth")
if not checkpoint.exists():
    raise FileNotFoundError(checkpoint)

shutil.copy2(checkpoint, "/kaggle/working/dinosaur.pth")
print("Production checkpoint:", checkpoint, checkpoint.stat().st_size / 1024**2, "MB")
```
