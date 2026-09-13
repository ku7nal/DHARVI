import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from training.gamus_multitask import (
    CLASS_COUNT,
    GamusSample,
    decode_class_mask,
    discover_samples,
    load_sample,
    MultitaskDepthAnythingModel,
    multitask_loss,
    reconstruction_metrics,
    split_by_group,
)
from app.semantic_contract import BUILDING_CLASS, CLASS_NAMES


class GamusDataTests(unittest.TestCase):
    def test_official_gamus_taxonomy_is_seven_classes_with_buildings_at_three(self) -> None:
        self.assertEqual(CLASS_NAMES, ("others", "ground", "low_vegetation", "building", "water", "road", "tree"))
        self.assertEqual(CLASS_COUNT, 7)
        self.assertEqual(BUILDING_CLASS, 3)

    def _write_sample(self, root: Path, group: str, name: str, size: tuple[int, int] = (8, 6)) -> None:
        for directory in ("images", "heights", "classes"):
            (root / directory / group).mkdir(parents=True, exist_ok=True)
        width, height = size
        Image.new("RGB", size, "#8899aa").save(root / "images" / group / f"{name}.png")
        Image.fromarray(np.full((height, width), 4, dtype=np.uint8)).save(root / "heights" / group / f"{name}.png")
        labels = np.tile(np.arange(width, dtype=np.uint8) % CLASS_COUNT, (height, 1))
        Image.fromarray(labels).save(root / "classes" / group / f"{name}.png")

    def test_discovery_and_group_split_preserve_aligned_triplets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_sample(root, "city-a", "tile-1")
            self._write_sample(root, "city-b", "tile-2")

            samples = discover_samples(root)
            train, validation = split_by_group(samples, ["city-b"])

            self.assertEqual(len(samples), 2)
            self.assertEqual([sample.group for sample in train], ["city-a"])
            self.assertEqual([sample.group for sample in validation], ["city-b"])
            image, height, classes, valid = load_sample(samples[0])
            self.assertEqual(image.shape[:2], height.shape)
            self.assertEqual(height.shape, classes.shape)
            self.assertTrue(np.all(valid))

    def test_alignment_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_sample(root, "city-a", "tile-1")
            Image.new("L", (4, 4), 1).save(root / "classes" / "city-a" / "tile-1.png")
            sample = discover_samples(root)[0]
            with self.assertRaisesRegex(ValueError, "Spatial alignment mismatch"):
                load_sample(sample)

    def test_rgb_classes_require_an_explicit_palette(self) -> None:
        values = np.asarray([[[10, 40]], [[20, 50]], [[30, 60]]], dtype=np.uint8)
        with self.assertRaisesRegex(ValueError, "explicit palette"):
            decode_class_mask(values)
        decoded = decode_class_mask(values, {(10, 20, 30): 0, (40, 50, 60): 2})
        np.testing.assert_array_equal(decoded, [[0, 2]])


class GamusMetricTests(unittest.TestCase):
    def test_kaggle_metric_report_contains_height_semantic_and_boundary_scores(self) -> None:
        import torch
        from types import SimpleNamespace

        from training.kaggle_gamus_train import evaluate_loader

        class PerfectModel:
            def eval(self):
                return self

            def __call__(self, image):
                batch, _, height, width = image.shape
                classes = torch.full((batch, height, width), BUILDING_CLASS, dtype=torch.long)
                semantic = torch.full((batch, CLASS_COUNT, height, width), -10.0)
                semantic.scatter_(1, classes[:, None], 10.0)
                boundary = torch.full((batch, 1, height, width), 10.0)
                return {
                    "height": torch.ones((batch, 1, height, width)),
                    "semantic": semantic,
                    "boundary": boundary,
                }

        batch = {
            "image": torch.zeros((1, 3, 2, 2)),
            "height": torch.ones((1, 1, 2, 2)),
            "classes": torch.full((1, 2, 2), BUILDING_CLASS, dtype=torch.long),
            "valid": torch.ones((1, 1, 2, 2), dtype=torch.bool),
            "boundary": torch.ones((1, 1, 2, 2)),
        }
        metrics = evaluate_loader(PerfectModel(), [batch], torch.device("cpu"))

        self.assertEqual(metrics["height_rmse"], 0.0)
        self.assertEqual(metrics["height_mae"], 0.0)
        self.assertEqual(metrics["height_correlation"], 0.0)
        self.assertEqual(metrics["building_iou"], 1.0)
        self.assertEqual(metrics["building_boundary_f1"], 1.0)
        self.assertEqual(metrics["per_class_iou"]["building"], 1.0)

    def test_multitask_model_exposes_height_and_semantic_heads(self) -> None:
        import torch
        import torch.nn as nn
        from types import SimpleNamespace

        class FakeBase(nn.Module):
            config = SimpleNamespace(hidden_size=4)

            def forward(self, pixel_values, output_hidden_states=True):
                batch, _, height, width = pixel_values.shape
                features = torch.ones((batch, 4, max(1, height // 2), max(1, width // 2)))
                return SimpleNamespace(
                    predicted_depth=torch.ones((batch, height, width)),
                    hidden_states=(features,),
                )

        model = MultitaskDepthAnythingModel(FakeBase(), torch).to_module()
        outputs = model(torch.zeros((1, 3, 8, 8)))
        self.assertEqual(tuple(outputs["height"].shape), (1, 1, 8, 8))
        self.assertEqual(tuple(outputs["semantic"].shape), (1, CLASS_COUNT, 8, 8))

    def test_multitask_loss_and_metrics_are_finite_for_valid_targets(self) -> None:
        import torch

        target_height = torch.ones((1, 1, 4, 4))
        target_classes = torch.full((1, 4, 4), BUILDING_CLASS, dtype=torch.long)
        outputs = {
            "height": target_height.clone(),
            "semantic": torch.zeros((1, CLASS_COUNT, 4, 4)),
        }
        outputs["semantic"][:, BUILDING_CLASS] = 4
        targets = {
            "height": target_height,
            "classes": target_classes,
            "valid": torch.ones((1, 1, 4, 4), dtype=torch.bool),
        }
        losses = multitask_loss(outputs, targets)
        self.assertTrue(torch.isfinite(losses["total"]))

        metrics = reconstruction_metrics(
            np.ones((4, 4)),
            np.ones((4, 4)),
            np.concatenate([np.zeros((3, 4, 4)), np.full((1, 4, 4), 4), np.zeros((CLASS_COUNT - 4, 4, 4))]),
            np.full((4, 4), BUILDING_CLASS, dtype=np.int64),
            np.ones((4, 4), dtype=bool),
        )
        self.assertEqual(metrics["height_rmse"], 0.0)
        self.assertEqual(metrics["height_mae"], 0.0)
        self.assertEqual(metrics["semantic_miou"], 1.0)
        self.assertEqual(metrics["building_f1"], 1.0)


if __name__ == "__main__":
    unittest.main()
