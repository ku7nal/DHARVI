from pathlib import Path

import numpy as np
from PIL import Image


class ModelUnavailableError(RuntimeError):
    """Raised when the fine-tuned inference model cannot be loaded."""


class DepthAnythingModelService:
    model_id = "depth-anything/Depth-Anything-V2-Small-hf"
    input_size = 518

    def __init__(self, checkpoint_path: Path, device: str | None = None) -> None:
        self.checkpoint_path = checkpoint_path
        self.device_name = device
        self._model = None
        self._torch = None

    def _load_model(self):
        if self._model is not None:
            return self._model

        try:
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
        image = image.convert("RGB")
        if image.width < self.input_size or image.height < self.input_size:
            scale = self.input_size / min(image.size)
            resized_size = (
                max(self.input_size, round(image.width * scale)),
                max(self.input_size, round(image.height * scale)),
            )
            image = image.resize(resized_size, Image.Resampling.BICUBIC)
        left = (image.width - self.input_size) // 2
        top = (image.height - self.input_size) // 2
        cropped = image.crop((left, top, left + self.input_size, top + self.input_size))
        pixels = np.asarray(cropped, dtype=np.float32) / 255.0
        mean = np.asarray([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.asarray([0.229, 0.224, 0.225], dtype=np.float32)
        normalized = (pixels - mean) / std
        return self._torch.from_numpy(normalized).permute(2, 0, 1).unsqueeze(0).float()

    def predict(self, image: Image.Image) -> np.ndarray:
        try:
            model = self._load_model()
            tensor = self._preprocess(image).to(self.device_name)
            with self._torch.inference_mode():
                prediction = model(tensor)[0, 0].detach().cpu().numpy()
            return np.maximum(prediction.astype(np.float32), 0.0)
        except ModelUnavailableError:
            raise
        except Exception as error:
            raise ModelUnavailableError(f"The fine-tuned model failed during inference: {error}") from error
