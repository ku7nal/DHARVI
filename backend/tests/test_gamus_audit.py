import json
import tempfile
import unittest
from pathlib import Path

import h5py
import numpy as np

from training.gamus_audit import DatasetAuditError, audit_dataset


class GamusAuditTests(unittest.TestCase):
    def _write_dataset(self, root: Path, *, include_orphan: bool = False) -> None:
        for split in ("train", "val", "test"):
            for directory in ("images", "heights", "classes"):
                (root / directory / split).mkdir(parents=True, exist_ok=True)

            image_name = f"DC_{split}_01_RGB.h5"
            height_name = f"DC_{split}_01_AGL.h5"
            class_name = f"DC_{split}_01_classes.h5"
            with h5py.File(root / "images" / split / image_name, "w") as file:
                file.create_dataset("image", data=np.zeros((4, 5, 3), dtype=np.uint8))
            with h5py.File(root / "heights" / split / height_name, "w") as file:
                file.create_dataset("height", data=np.array([[0, 2, 4, np.nan, 8], [1, 3, 5, 7, 9], [0, 0, 0, 0, 0], [2, 2, 2, 2, 2]], dtype=np.float32))
            with h5py.File(root / "classes" / split / class_name, "w") as file:
                file.create_dataset("classes", data=np.array([[1, 3, 3, 3, 6], [1, 3, 3, 5, 6], [1, 1, 1, 1, 1], [2, 2, 2, 2, 2]], dtype=np.uint8))

        if include_orphan:
            with h5py.File(root / "heights" / "train" / "unmatched_AGL.h5", "w") as file:
                file.create_dataset("height", data=np.zeros((4, 5), dtype=np.float32))

    def test_audit_pairs_suffix_variants_and_writes_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_dataset(root)
            output = root / "artifacts" / "manifest.json"

            manifest = audit_dataset(root, output, dataset_id="owner/gamus", dataset_revision="42")

            self.assertEqual(manifest["dataset"]["revision"], "42")
            self.assertEqual(manifest["splits"]["train"]["sample_count"], 1)
            self.assertEqual(manifest["total_sample_count"], 3)
            sample = manifest["samples"][0]
            self.assertEqual(sample["group"], "DC")
            self.assertEqual(sample["shapes"]["image"], [4, 5, 3])
            self.assertEqual(sample["dataset_keys"], {"image": "image", "height": "height", "classes": "classes"})
            self.assertEqual(sample["invalid_pixels"]["height_nonfinite"], 1)
            self.assertEqual(sample["class_ids"], [1, 2, 3, 5, 6])
            self.assertAlmostEqual(sample["building_pixel_fraction"], 4 / 19)
            self.assertEqual(json.loads(output.read_text())["total_sample_count"], 3)

    def test_audit_rejects_orphan_target_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_dataset(root, include_orphan=True)

            with self.assertRaisesRegex(DatasetAuditError, "unmatched"):
                audit_dataset(root, root / "manifest.json", dataset_id="owner/gamus", dataset_revision="42")

    def test_audit_requires_dataset_revision(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_dataset(root)

            with self.assertRaisesRegex(ValueError, "dataset revision"):
                audit_dataset(root, root / "manifest.json", dataset_id="owner/gamus", dataset_revision="")

    def test_audit_rejects_invalid_class_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_dataset(root)
            with h5py.File(root / "classes" / "train" / "DC_train_01_classes.h5", "r+") as file:
                file["classes"][0, 0] = 99

            with self.assertRaisesRegex(DatasetAuditError, "Invalid semantic class IDs"):
                audit_dataset(root, root / "manifest.json", dataset_id="owner/gamus", dataset_revision="42")


if __name__ == "__main__":
    unittest.main()
