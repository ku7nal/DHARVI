from pathlib import Path
import os
import platform

import numpy as np
from PIL import Image


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
            base_model = AutoModelForDepthEstimation.from_pretrained(self.model_id)
            input_size = self.input_size

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
            state_dict = torch.load(self.checkpoint_path, map_location="cpu", weights_only=True)
            model.load_state_dict(state_dict, strict=True)
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
        try:
            model = self._load_model()
            image = image.convert("RGB")
            prediction_sum = np.zeros((image.height, image.width), dtype=np.float32)
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
                        tile_prediction = model(tensor)[0, 0].detach().cpu().numpy().astype(np.float32)
                        # TTA catches the strongest directional bias in aerial imagery.
                        flipped = tile.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                        flipped_prediction = model(self._preprocess(flipped).to(self.device_name))[0, 0]
                        flipped_prediction = flipped_prediction.detach().cpu().numpy().astype(np.float32)
                        flipped_prediction = np.fliplr(flipped_prediction)
                        tile_prediction = (tile_prediction + flipped_prediction) * 0.5
                        tile_prediction = np.maximum(tile_prediction, 0.0)
                        tile_prediction = tile_prediction[:valid_height, :valid_width]
                        tile_weight = window[:valid_height, :valid_width]
                        prediction_sum[top:top + valid_height, left:left + valid_width] += tile_prediction * tile_weight
                        weight_sum[top:top + valid_height, left:left + valid_width] += tile_weight

            return np.divide(prediction_sum, np.maximum(weight_sum, 1e-6)).astype(np.float32)
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
