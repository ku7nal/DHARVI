from pathlib import Path
import os
import platform

import numpy as np
from PIL import Image

from app.semantic_contract import CLASS_COUNT, CLASS_NAMES


class ModelUnavailableError(RuntimeError):
    """Raised when the fine-tuned inference model cannot be loaded."""


class DepthAnythingModelService:
    model_id = "depth-anything/Depth-Anything-V2-Small-hf"
    input_size = 518
    tile_overlap = 0.5

    def __init__(self, checkpoint_path: Path, device: str | None = None) -> None:
        self.checkpoint_path = checkpoint_path
        self.device_name = device
        self._model = None
        self._torch = None
        self._multitask = False

    def _load_model(self):
        if self._model is not None:
            return self._model

        try:
            self._configure_openmp_compatibility()
            import torch
            import torch.nn as nn
            from transformers import AutoModelForDepthEstimation
        except ImportError as error:
            raise ModelUnavailableError(
                "Model dependencies are missing. Install backend requirements before uploading an image."
            ) from error

        if not self.checkpoint_path.exists():
            raise ModelUnavailableError(f"Model checkpoint was not found at {self.checkpoint_path}.")

        try:
            checkpoint = torch.load(self.checkpoint_path, map_location="cpu", weights_only=False)
            checkpoint_state = checkpoint.get("state_dict", checkpoint) if isinstance(checkpoint, dict) else checkpoint
            checkpoint_model_id = checkpoint.get("model_id") if isinstance(checkpoint, dict) else None
            checkpoint_classes = tuple(checkpoint.get("class_names", ())) if isinstance(checkpoint, dict) else ()
            if checkpoint_classes and checkpoint_classes != CLASS_NAMES:
                raise ModelUnavailableError(
                    "The checkpoint uses an incompatible GAMUS taxonomy; "
                    f"expected {CLASS_NAMES}, got {checkpoint_classes}."
                )
            model_id = checkpoint_model_id or self.model_id
            input_size = int(checkpoint.get("image_size", self.input_size)) if isinstance(checkpoint, dict) else self.input_size
            self.model_id = model_id
            self.input_size = input_size

            base_model = AutoModelForDepthEstimation.from_pretrained(model_id)

            is_multitask = any(key.startswith("base.") for key in checkpoint_state) and "semantic_head.0.weight" in checkpoint_state

            if is_multitask:
                channels = int(getattr(base_model.config, "hidden_size", getattr(base_model.config, "reassemble_hidden_size", 384)))

                class DepthAnythingMultitaskModel(nn.Module):
                    def __init__(self, base):
                        super().__init__()
                        self.base = base
                        self.semantic_head = nn.Sequential(
                            nn.Conv2d(channels, 256, 3, padding=1),
                            nn.GELU(),
                            nn.Conv2d(256, CLASS_COUNT, 1),
                        )
                        self.boundary_head = nn.Sequential(
                            nn.Conv2d(channels, 128, 3, padding=1),
                            nn.GELU(),
                            nn.Conv2d(128, 1, 1),
                        )

                    def forward(self, pixel_values):
                        import math

                        outputs = self.base(pixel_values=pixel_values, output_hidden_states=True)
                        height = nn.functional.interpolate(
                            outputs.predicted_depth.unsqueeze(1),
                            size=pixel_values.shape[-2:],
                            mode="bilinear",
                            align_corners=True,
                        )
                        features = outputs.hidden_states[-1]
                        if features.ndim == 3:
                            side = int(math.sqrt(features.shape[1]))
                            if side * side != features.shape[1]:
                                features = features[:, 1:]
                                side = int(math.sqrt(features.shape[1]))
                            features = features[:, :side * side].transpose(1, 2).reshape(features.shape[0], features.shape[2], side, side)
                        semantic = nn.functional.interpolate(self.semantic_head(features), size=pixel_values.shape[-2:], mode="bilinear", align_corners=False)
                        boundary = nn.functional.interpolate(self.boundary_head(features), size=pixel_values.shape[-2:], mode="bilinear", align_corners=False)
                        return {"height": torch.relu(height), "semantic": semantic, "boundary": boundary}

                model = DepthAnythingMultitaskModel(base_model)
                model.load_state_dict(checkpoint_state, strict=True)
                self._multitask = True
            else:
                class DepthAnythingHeightModel(nn.Module):
                    def __init__(self, base):
                        super().__init__()
                        self.model = base
                        for parameter in self.model.backbone.embeddings.parameters():
                            parameter.requires_grad = False

                    def forward(self, pixel_values):
                        outputs = self.model(pixel_values=pixel_values)
                        predicted_height = nn.functional.interpolate(
                            outputs.predicted_depth.unsqueeze(1),
                            size=(input_size, input_size),
                            mode="bilinear",
                            align_corners=True,
                        )
                        return torch.relu(predicted_height)

                model = DepthAnythingHeightModel(base_model)
                model.load_state_dict(checkpoint_state, strict=True)

            if self.device_name:
                device = self.device_name
            elif torch.cuda.is_available():
                device = "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                device = "mps"
            else:
                device = "cpu"
            model.to(device)
            model.eval()
            self._model = model
            self._torch = torch
            self.device_name = device
            return model
        except ModelUnavailableError:
            raise
        except Exception as error:
            raise ModelUnavailableError(f"The fine-tuned model could not be loaded: {error}") from error

    def _preprocess(self, image: Image.Image):
        pixels = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
        mean = np.asarray([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.asarray([0.229, 0.224, 0.225], dtype=np.float32)
        normalized = (pixels - mean) / std
        return self._torch.from_numpy(normalized).permute(2, 0, 1).unsqueeze(0).float()

    def _tile_starts(self, length: int) -> list[int]:
        if length <= self.input_size:
            return [0]
        stride = max(1, round(self.input_size * (1 - self.tile_overlap)))
        starts = list(range(0, length - self.input_size + 1, stride))
        final_start = length - self.input_size
        if starts[-1] != final_start:
            starts.append(final_start)
        return starts

    def _prepare_tile(self, image: Image.Image, left: int, top: int) -> tuple[Image.Image, tuple[int, int, int, int]]:
        """Return a fixed-size tile and the unpadded region it represents."""
        right = min(left + self.input_size, image.width)
        bottom = min(top + self.input_size, image.height)
        tile = image.crop((left, top, right, bottom))
        valid_width, valid_height = tile.size
        if tile.size != (self.input_size, self.input_size):
            pad_right = self.input_size - tile.width
            pad_bottom = self.input_size - tile.height
            # Reflect padding avoids introducing a black edge into the model.
            tile = Image.fromarray(np.pad(
                np.asarray(tile),
                ((0, pad_bottom), (0, pad_right), (0, 0)),
                mode="reflect",
            ).astype(np.uint8))
        return tile, (0, 0, valid_width, valid_height)

    def predict(self, image: Image.Image) -> np.ndarray:
        return self.predict_result(image)["height"]

    def predict_result(self, image: Image.Image) -> dict[str, np.ndarray]:
        try:
            model = self._load_model()
            image = image.convert("RGB")
            prediction_sum = np.zeros((image.height, image.width), dtype=np.float32)
            semantic_sum = np.zeros((CLASS_COUNT, image.height, image.width), dtype=np.float32) if self._multitask else None
            weight_sum = np.zeros_like(prediction_sum)
            # A smooth window prevents seams where adjacent tiles meet.
            window_1d = np.hanning(self.input_size).astype(np.float32)
            window = np.outer(window_1d, window_1d)
            window = np.maximum(window, 1e-3)

            with self._torch.inference_mode():
                for top in self._tile_starts(image.height):
                    for left in self._tile_starts(image.width):
                        tile, (_, _, valid_width, valid_height) = self._prepare_tile(image, left, top)
                        tensor = self._preprocess(tile).to(self.device_name)
                        tile_output = model(tensor)
                        if self._multitask:
                            tile_prediction = tile_output["height"][0, 0].detach().cpu().numpy().astype(np.float32)
                            tile_semantic = tile_output["semantic"][0].detach().cpu().numpy().astype(np.float32)
                        else:
                            tile_prediction = tile_output[0, 0].detach().cpu().numpy().astype(np.float32)
                        # TTA catches the strongest directional bias in aerial imagery.
                        flipped = tile.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                        flipped_output = model(self._preprocess(flipped).to(self.device_name))
                        if self._multitask:
                            flipped_prediction = flipped_output["height"][0, 0].detach().cpu().numpy().astype(np.float32)
                            flipped_semantic = flipped_output["semantic"][0].detach().cpu().numpy().astype(np.float32)
                            flipped_semantic = np.flip(flipped_semantic, axis=2)
                        else:
                            flipped_prediction = flipped_output[0, 0].detach().cpu().numpy().astype(np.float32)
                        flipped_prediction = np.fliplr(flipped_prediction)
                        tile_prediction = (tile_prediction + flipped_prediction) * 0.5
                        tile_prediction = np.maximum(tile_prediction, 0.0)
                        tile_prediction = tile_prediction[:valid_height, :valid_width]
                        tile_weight = window[:valid_height, :valid_width]
                        prediction_sum[top:top + valid_height, left:left + valid_width] += tile_prediction * tile_weight
                        if semantic_sum is not None:
                            tile_semantic = (tile_semantic + flipped_semantic) * 0.5
                            semantic_sum[:, top:top + valid_height, left:left + valid_width] += tile_semantic[:, :valid_height, :valid_width] * tile_weight
                        weight_sum[top:top + valid_height, left:left + valid_width] += tile_weight

            result: dict[str, np.ndarray] = {
                "height": np.divide(prediction_sum, np.maximum(weight_sum, 1e-6)).astype(np.float32),
            }
            if semantic_sum is not None:
                result["semantic"] = np.divide(semantic_sum, np.maximum(weight_sum, 1e-6)[None]).astype(np.float32)
            return result
        except ModelUnavailableError:
            raise
        except Exception as error:
            raise ModelUnavailableError(f"The fine-tuned model failed during inference: {error}") from error

    @staticmethod
    def _configure_openmp_compatibility() -> None:
        """Keep the macOS Homebrew/PyTorch wheel combination from aborting startup.

        Some current macOS Python 3.14 PyTorch distributions load their bundled
        ``libomp`` and Homebrew's ``libomp`` in the same process. The runtime aborts
        before PyTorch can be imported. This environment flag is PyTorch/LLVM's
        compatibility escape hatch; it is limited to macOS and can be disabled when
        the environment is rebuilt with a single OpenMP runtime.
        """
        if platform.system() == "Darwin" and os.getenv("DEPTHWIZARD_OPENMP_COMPAT", "1") == "1":
            os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
